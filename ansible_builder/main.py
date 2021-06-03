import logging
import os
import textwrap
import yaml

from . import constants
from .exceptions import DefinitionError
from .steps import (
    AdditionalBuildSteps, BuildContextSteps, GalaxyInstallSteps, GalaxyCopySteps, AnsibleConfigSteps
)
from .utils import run_command, copy_file


logger = logging.getLogger(__name__)

# Files that need to be moved into the build context, and their naming inside the context
CONTEXT_FILES = {
    'galaxy': 'requirements.yml',
    'python': 'requirements.txt',
    'system': 'bindep.txt',
}

ALLOWED_KEYS = [
    'version',
    'build_arg_defaults',
    'dependencies',
    'ansible_config',
    'additional_build_steps',
]


class AnsibleBuilder:
    def __init__(self, action=None,
                 filename=constants.default_file,
                 build_args=None,
                 build_context=constants.default_build_context,
                 tag=constants.default_tag,
                 container_runtime=constants.default_container_runtime,
                 output_filename=None,
                 verbosity=constants.default_verbosity):
        self.action = action
        self.definition = UserDefinition(filename=filename)

        self.tag = tag
        self.build_context = build_context
        self.build_outputs_dir = os.path.join(
            build_context, constants.user_content_subfolder)
        self.container_runtime = container_runtime
        self.build_args = build_args or {}
        self.containerfile = Containerfile(
            definition=self.definition,
            build_context=self.build_context,
            container_runtime=self.container_runtime,
            output_filename=output_filename,
            tag=self.tag)
        self.verbosity = verbosity

    @property
    def version(self):
        return self.definition.version

    @property
    def ansible_config(self):
        return self.definition.ansible_config

    @property
    def build_command(self):
        command = [
            self.container_runtime, "build",
            "-f", self.containerfile.path,
            "-t", self.tag,
        ]

        for key, value in self.build_args.items():
            if value:
                build_arg = f"--build-arg={key}={value}"
            else:
                build_arg = f"--build-arg={key}"

            command.append(build_arg)

        command.append(self.build_context)

        return command

    def build(self):
        # File preparation
        self.containerfile.create_folder_copy_files()
        self.containerfile.prepare_ansible_config_file()

        # First stage, galaxy
        self.containerfile.prepare_galaxy_stage_steps()
        self.containerfile.prepare_build_context()
        self.containerfile.prepare_galaxy_install_steps()

        # Second stage, builder
        self.containerfile.prepare_build_stage_steps()
        self.containerfile.prepare_galaxy_copy_steps()
        self.containerfile.prepare_introspect_assemble_steps()

        # Second stage
        self.containerfile.prepare_final_stage_steps()
        self.containerfile.prepare_prepended_steps()
        self.containerfile.prepare_galaxy_copy_steps()
        self.containerfile.prepare_system_runtime_deps_steps()
        self.containerfile.prepare_appended_steps()
        logger.debug('Rewriting Containerfile to capture collection requirements')
        self.containerfile.write()
        run_command(self.build_command)
        return True


class BaseDefinition:
    """Subclasses should populate these properties in the __init__ method
    self.raw - a dict that basically is the definition
    self.reference_path - the folder which dependencies are specified relative to
    """

    @property
    def version(self):
        version = self.raw.get('version')

        if not version:
            raise ValueError("Expected top-level 'version' key to be present.")

        return str(version)

    @property
    def ansible_config(self):
        ansible_config = self.raw.get('ansible_config')

        if not ansible_config:
            pass
        else:
            return str(ansible_config)


class UserDefinition(BaseDefinition):
    def __init__(self, filename):
        self.filename = filename
        self.reference_path = os.path.dirname(filename)

        try:
            with open(filename, 'r') as f:
                y = yaml.safe_load(f)
                self.raw = y if y else {}
        except FileNotFoundError:
            raise DefinitionError(textwrap.dedent("""
            Could not detect '{0}' file in this directory.
            Use -f to specify a different location.
            """).format(filename))
        except (yaml.parser.ParserError, yaml.scanner.ScannerError) as e:
            raise DefinitionError(textwrap.dedent("""
            An error occured while parsing the definition file:
            {0}
            """).format(str(e)))

        if not isinstance(self.raw, dict):
            raise DefinitionError("Definition must be a dictionary, not {0}".format(type(self.raw).__name__))

        if not isinstance(self.raw.get('dependencies'), dict):
            raise DefinitionError(textwrap.dedent(
                f"""
                Error: Unknown type {type(self.raw.get('dependencies'))} found for dependencies, must be a dict.\n
                Allowed options are:
                {list(CONTEXT_FILES.keys())}
                """)
            )

        # Populate build arg defaults, which are customizable in definition
        self.build_arg_defaults = {}
        user_build_arg_defaults = self.raw.get('build_arg_defaults', {})
        if not isinstance(user_build_arg_defaults, dict):
            user_build_arg_defaults = {}  # so that validate method can throw error
        for key, default_value in constants.build_arg_defaults.items():
            self.build_arg_defaults[key] = user_build_arg_defaults.get(key, default_value)

    def get_additional_commands(self):
        """Gets additional commands from the exec env file, if any are specified.
        """
        commands = self.raw.get('additional_build_steps')
        return commands

    def get_dep_abs_path(self, entry):
        """Unique to the user EE definition, files can be referenced by either
        an absolute path or a path relative to the EE definition folder
        This method will return the absolute path.
        """
        req_file = self.raw.get('dependencies', {}).get(entry)

        if not req_file:
            return None

        if os.path.isabs(req_file):
            return req_file

        return os.path.join(self.reference_path, req_file)

    def validate(self):
        # Check that all specified keys in the definition file are valid.
        def_file_dict = self.raw
        yaml_keys = set(def_file_dict.keys())
        invalid_keys = yaml_keys - set(ALLOWED_KEYS)
        if invalid_keys:
            raise DefinitionError(textwrap.dedent(
                f"""
                Error: Unknown yaml key(s), {invalid_keys}, found in the definition file.\n
                Allowed options are:
                {ALLOWED_KEYS}
                """)
            )
        
        dependencies_keys = set(self.raw.get('dependencies'))
        invalid_dependencies_keys = dependencies_keys - set(CONTEXT_FILES.keys())
        if invalid_dependencies_keys:
            raise DefinitionError(textwrap.dedent(
                f"""
                Error: Unknown yaml key(s), {invalid_dependencies_keys}, found in dependencies.\n
                Allowed options are:
                {list(CONTEXT_FILES.keys())}
                """)
            )

        for item in CONTEXT_FILES:
            requirement_path = self.get_dep_abs_path(item)
            if requirement_path:
                if not os.path.exists(requirement_path):
                    raise DefinitionError("Dependency file {0} does not exist.".format(requirement_path))

        build_arg_defaults = self.raw.get('build_arg_defaults')
        if build_arg_defaults:
            if not isinstance(build_arg_defaults, dict):
                raise DefinitionError(
                    f"Error: Unknown type {type(build_arg_defaults)} found for build_arg_defaults; "
                    f"must be a dict."
                )
            unexpected_keys = set(build_arg_defaults.keys()) - set(constants.build_arg_defaults)
            if unexpected_keys:
                raise DefinitionError(
                    f"Keys {unexpected_keys} are not allowed in 'build_arg_defaults'."
                )
            for key, value in constants.build_arg_defaults.items():
                user_value = build_arg_defaults.get(key)
                if user_value and not isinstance(user_value, str):
                    raise DefinitionError(
                        f"Expected build_arg_defaults.{key} to be a string; "
                        f"Found a {type(user_value)} instead."
                    )

        additional_cmds = self.get_additional_commands()
        if additional_cmds:
            if not isinstance(additional_cmds, dict):
                raise DefinitionError(textwrap.dedent("""
                    Expected 'additional_build_steps' in the provided definition file to be a dictionary
                    with keys 'prepend' and/or 'append'; found a {0} instead.
                    """).format(type(additional_cmds).__name__))

            expected_keys = frozenset(('append', 'prepend'))
            unexpected_keys = set(additional_cmds.keys()) - expected_keys
            if unexpected_keys:
                raise DefinitionError(
                    f"Keys {*unexpected_keys,} are not allowed in 'additional_build_steps'."
                )

        ansible_config_path = self.raw.get('ansible_config')
        if ansible_config_path:
            if not isinstance(ansible_config_path, str):
                raise DefinitionError(textwrap.dedent("""
                    Expected 'ansible_config' in the provided definition file to
                    be a string; found a {0} instead.
                    """).format(type(ansible_config_path).__name__))


class Containerfile:
    newline_char = '\n'

    def __init__(self, definition,
                 build_context=None,
                 container_runtime=None,
                 output_filename=None,
                 tag=None):

        self.build_context = build_context
        self.build_outputs_dir = os.path.join(
            build_context, constants.user_content_subfolder)
        self.definition = definition
        if output_filename is None:
            filename = constants.runtime_files[container_runtime]
        else:
            filename = output_filename
        self.path = os.path.join(self.build_context, filename)
        self.container_runtime = container_runtime
        self.tag = tag
        # Build args all need to go at top of file to avoid errors
        self.steps = [
            "ARG EE_BASE_IMAGE={}".format(
                self.definition.build_arg_defaults['EE_BASE_IMAGE']
            ),
            "ARG EE_BUILDER_IMAGE={}".format(
                self.definition.build_arg_defaults['EE_BUILDER_IMAGE']
            ),
        ]

    def create_folder_copy_files(self):
        """Creates the build context file for this Containerfile
        moves files from the definition into the folder
        """
        # courteously validate items before starting to write files
        self.definition.validate()

        os.makedirs(self.build_outputs_dir, exist_ok=True)

        for item, new_name in CONTEXT_FILES.items():
            requirement_path = self.definition.get_dep_abs_path(item)
            if requirement_path is None:
                continue
            dest = os.path.join(
                self.build_context, constants.user_content_subfolder, new_name)
            copy_file(requirement_path, dest)

        if self.definition.ansible_config:
            copy_file(
                self.definition.ansible_config,
                os.path.join(self.build_outputs_dir, 'ansible.cfg')
            )

    def prepare_ansible_config_file(self):
        ansible_config_file_path = self.definition.ansible_config
        if ansible_config_file_path:
            context_file_path = os.path.join(
                constants.user_content_subfolder, 'ansible.cfg')
            return self.steps.extend(AnsibleConfigSteps(context_file_path))

    def prepare_prepended_steps(self):
        additional_prepend_steps = self.definition.get_additional_commands()
        if additional_prepend_steps:
            prepended_steps = additional_prepend_steps.get('prepend')
            if prepended_steps:
                return self.steps.extend(AdditionalBuildSteps(prepended_steps))

        return False

    def prepare_appended_steps(self):
        additional_append_steps = self.definition.get_additional_commands()
        if additional_append_steps:
            appended_steps = additional_append_steps.get('append')
            if appended_steps:
                return self.steps.extend(AdditionalBuildSteps(appended_steps))

        return False

    def prepare_build_context(self):
        if any(self.definition.get_dep_abs_path(thing) for thing in ('galaxy', 'system', 'python')):
            self.steps.extend(BuildContextSteps())
        return self.steps

    def prepare_galaxy_install_steps(self):
        if self.definition.get_dep_abs_path('galaxy'):
            self.steps.extend(GalaxyInstallSteps(CONTEXT_FILES['galaxy']))
        return self.steps

    def prepare_introspect_assemble_steps(self):
        # The introspect/assemble block is valid if there are any form of requirements
        if any(self.definition.get_dep_abs_path(thing) for thing in ('galaxy', 'system', 'python')):

            introspect_cmd = "RUN ansible-builder introspect --sanitize"

            requirements_file_exists = os.path.exists(os.path.join(
                self.build_outputs_dir, CONTEXT_FILES['python']
            ))
            if requirements_file_exists:
                relative_requirements_path = os.path.join(constants.user_content_subfolder, CONTEXT_FILES['python'])
                self.steps.append(f"ADD {relative_requirements_path} {CONTEXT_FILES['python']}")
                # WORKDIR is /build, so we use the (shorter) relative paths there
                introspect_cmd += " --user-pip={0}".format(CONTEXT_FILES['python'])
            bindep_exists = os.path.exists(os.path.join(self.build_outputs_dir, CONTEXT_FILES['system']))
            if bindep_exists:
                relative_bindep_path = os.path.join(constants.user_content_subfolder, CONTEXT_FILES['system'])
                self.steps.append(f"ADD {relative_bindep_path} {CONTEXT_FILES['system']}")
                introspect_cmd += " --user-bindep={0}".format(CONTEXT_FILES['system'])

            introspect_cmd += " --write-bindep=/tmp/src/bindep.txt --write-pip=/tmp/src/requirements.txt"

            self.steps.append(introspect_cmd)
            self.steps.append("RUN assemble")

        return self.steps

    def prepare_system_runtime_deps_steps(self):
        self.steps.extend([
            "COPY --from=builder /output/ /output/",
            "RUN /output/install-from-bindep && rm -rf /output/wheels",
        ])

        return self.steps

    def prepare_galaxy_stage_steps(self):
        self.steps.extend([
            "",
            "FROM $EE_BASE_IMAGE as galaxy",
            "ARG ANSIBLE_GALAXY_CLI_COLLECTION_OPTS={}".format(
                self.definition.build_arg_defaults['ANSIBLE_GALAXY_CLI_COLLECTION_OPTS']
            ),
            "USER root",
            ""
        ])

        return self.steps

    def prepare_build_stage_steps(self):
        self.steps.extend([
            "",
            "FROM $EE_BUILDER_IMAGE as builder"
            "",
        ])

        return self.steps

    def prepare_final_stage_steps(self):
        self.steps.extend([
            "",
            "FROM $EE_BASE_IMAGE",
            "USER root"
            "",
        ])
        return self.steps

    def prepare_galaxy_copy_steps(self):
        if self.definition.get_dep_abs_path('galaxy'):
            self.steps.extend(GalaxyCopySteps())
        return self.steps

    def write(self):
        with open(self.path, 'w') as f:
            for step in self.steps:
                f.write(step + self.newline_char)

        return True
