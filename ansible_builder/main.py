import logging
import os
import textwrap
import yaml

from . import constants
from .exceptions import DefinitionError
from .steps import (
    AdditionalBuildSteps, GalaxyInstallSteps, GalaxyCopySteps, AnsibleConfigSteps
)
from .utils import run_command, write_file, copy_file
from .requirements import sanitize_requirements
import ansible_builder.introspect


logger = logging.getLogger(__name__)

# Files that need to be moved into the build context, and their naming inside the context
CONTEXT_FILES = {
    'galaxy': 'requirements.yml'
}

BINDEP_COMBINED = 'bindep_combined.txt'
PIP_COMBINED = 'requirements_combined.txt'

ALLOWED_KEYS = [
    'version',
    'base_image',
    'dependencies',
    'ansible_config',
    'additional_build_steps',
]


class AnsibleBuilder:
    def __init__(self, action=None,
                 filename=constants.default_file,
                 base_image=None,
                 build_context=constants.default_build_context,
                 tag=constants.default_tag,
                 container_runtime=constants.default_container_runtime,
                 verbosity=2):
        self.action = action
        self.definition = UserDefinition(filename=filename)

        # Handle precedence of the base image
        if base_image is not None:
            self.base_image = base_image
        if base_image is None:
            if self.definition.raw.get('base_image'):
                self.base_image = self.definition.raw.get('base_image')
            else:
                self.base_image = constants.default_base_image

        self.tag = tag
        self.build_context = build_context
        self.container_runtime = container_runtime
        self.containerfile = Containerfile(
            definition=self.definition,
            base_image=self.base_image,
            build_context=self.build_context,
            container_runtime=self.container_runtime,
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
        return [
            self.container_runtime, "build",
            "-f", self.containerfile.path,
            "-t", self.tag,
            self.build_context
        ]

    def run_in_container(self, command, **kwargs):
        wrapped_command = [self.container_runtime, 'run','--rm']

        wrapped_command.extend(['-v', f"{os.path.abspath(self.build_context)}:/context:Z"])

        wrapped_command.extend([self.tag] + command)

        return run_command(wrapped_command, **kwargs)

    def run_intermission(self):
        run_command(self.build_command, capture_output=True)

        rc, introspect_output = self.run_in_container(
            ['python3', '/context/introspect.py'], capture_output=True
        )
        collection_data = yaml.safe_load('\n'.join(introspect_output))

        # Add data from user definition, go from dicts to list
        collection_data['system']['user'] = self.definition.user_system
        collection_data['python']['user'] = self.definition.user_python
        system_lines = ansible_builder.introspect.simple_combine(collection_data['system'])
        python_lines = sanitize_requirements(collection_data['python'])

        if system_lines:
            bindep_file = os.path.join(self.build_context, BINDEP_COMBINED)
            write_file(bindep_file, system_lines + [''])

        if python_lines:
            pip_file = os.path.join(self.build_context, PIP_COMBINED)
            write_file(pip_file, python_lines)

        return (system_lines, python_lines)

    def build(self):
        # Phase 1 of Containerfile
        self.containerfile.create_folder_copy_files()
        self.containerfile.prepare_ansible_config_file()
        self.containerfile.prepare_galaxy_install_steps()
        logger.debug('Writing partial Containerfile without collection requirements')
        self.containerfile.write()
        system_lines, python_lines = self.run_intermission()

        # Phase 2 of Containerfile
        self.containerfile.prepare_build_stage_steps()
        self.containerfile.prepare_assemble_steps()

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

        self.user_python = self.read_dependency('python')
        self.user_system = self.read_dependency('system')

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

    def read_dependency(self, entry):
        requirement_path = self.get_dep_abs_path(entry)
        if not requirement_path:
            return []
        try:
            with open(requirement_path, 'r') as f:
                return f.read().split('\n')
        except FileNotFoundError:
            raise DefinitionError("Dependency file {0} does not exist.".format(requirement_path))

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

        for item in CONTEXT_FILES:
            requirement_path = self.get_dep_abs_path(item)
            if requirement_path:
                if not os.path.exists(requirement_path):
                    raise DefinitionError("Dependency file {0} does not exist.".format(requirement_path))

        ee_base_image = self.raw.get('base_image')
        if ee_base_image:
            if not isinstance(ee_base_image, str):
                raise DefinitionError(textwrap.dedent(
                    f"""
                    Error: Unknown type {type(ee_base_image)} found for base_image; must be a string.
                    """)
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
                 base_image=None,
                 container_runtime=None,
                 tag=None):

        self.build_context = build_context
        self.definition = definition
        filename = constants.runtime_files[container_runtime]
        self.path = os.path.join(self.build_context, filename)
        self.base_image = base_image
        self.builder_stage_image = 'quay.io/ansible/python-builder:latest'
        self.container_runtime = container_runtime
        self.tag = tag
        self.steps = [
            "FROM {0} as galaxy".format(self.base_image),
            ""
        ]

    def create_folder_copy_files(self):
        """Creates the build context file for this Containerfile
        moves files from the definition into the folder
        """
        # courteously validate items before starting to write files
        self.definition.validate()

        os.makedirs(self.build_context, exist_ok=True)

        for item, new_name in CONTEXT_FILES.items():
            requirement_path = self.definition.get_dep_abs_path(item)
            if requirement_path is None:
                continue
            dest = os.path.join(self.build_context, new_name)
            copy_file(requirement_path, dest)

        # copy introspect.py file from source into build context
        copy_file(
            ansible_builder.introspect.__file__,
            os.path.join(self.build_context, 'introspect.py')
        )

        if self.definition.ansible_config:
            copy_file(
                self.definition.ansible_config,
                os.path.join(self.build_context, 'ansible.cfg')
            )

    def prepare_ansible_config_file(self):
        ansible_config_file_path = self.definition.ansible_config
        if ansible_config_file_path:
            return self.steps.extend(AnsibleConfigSteps(ansible_config_file_path))

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

    def prepare_galaxy_install_steps(self):
        if self.definition.get_dep_abs_path('galaxy'):
            self.steps.extend(GalaxyInstallSteps(CONTEXT_FILES['galaxy']))
        return self.steps

    def prepare_assemble_steps(self):
        requirements_file_exists = os.path.exists(os.path.join(self.build_context, PIP_COMBINED))
        if requirements_file_exists:
            self.steps.append("ADD {0} /tmp/src/requirements.txt".format(PIP_COMBINED))

        bindep_exists = os.path.exists(os.path.join(self.build_context, BINDEP_COMBINED))
        if bindep_exists:
            self.steps.append("ADD {0} /tmp/src/bindep.txt".format(BINDEP_COMBINED))

        if requirements_file_exists or bindep_exists:
            self.steps.append("RUN assemble")

        return self.steps

    def prepare_system_runtime_deps_steps(self):
        requirements_file_exists = os.path.exists(os.path.join(self.build_context, PIP_COMBINED))
        bindep_exists = os.path.exists(os.path.join(self.build_context, BINDEP_COMBINED))

        if requirements_file_exists or bindep_exists:
            self.steps.extend([
                "COPY --from=builder /output/ /output/",
                "RUN /output/install-from-bindep && rm -rf /output/wheels",
            ])

        return self.steps

    def prepare_build_stage_steps(self):
        self.steps.extend([
            "",
            "FROM {0} as builder".format(self.builder_stage_image),
            "",
        ])
        return self.steps

    def prepare_final_stage_steps(self):
        self.steps.extend([
            "",
            "FROM {0}".format(self.base_image),
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
