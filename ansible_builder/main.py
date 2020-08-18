import os
import textwrap
import yaml

from . import constants
from .colors import MessageColors
from .exceptions import DefinitionError
from .steps import AdditionalBuildSteps, GalaxySteps, PipSteps, IntrospectionSteps, BindepSteps
from .utils import run_command, write_file, copy_file
from .requirements import sanitize_requirements
import ansible_builder.introspect


# Files that need to be moved into the build context, and their naming inside the context
CONTEXT_FILES = {
    'galaxy': 'requirements.yml',
    'python': 'requirements_user.txt',
    'system': 'bindep_user.txt'
}
BINDEP_COMBINED = 'bindep_combined.txt'
BINDEP_OUTPUT = 'bindep_output.txt'
PIP_COMBINED = 'requirements_combined.txt'


class AnsibleBuilder:
    def __init__(self, action=None,
                 filename=constants.default_file,
                 base_image=constants.default_base_image,
                 build_context=constants.default_build_context,
                 tag=constants.default_tag,
                 container_runtime=constants.default_container_runtime):
        self.action = action
        self.definition = UserDefinition(filename=filename)
        self.tag = tag
        self.build_context = build_context
        self.container_runtime = container_runtime
        self.containerfile = Containerfile(
            definition=self.definition,
            base_image=base_image,
            build_context=self.build_context,
            container_runtime=self.container_runtime,
            tag=self.tag)

    @property
    def version(self):
        return self.definition.version

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

        volumes = kwargs.pop('volumes', [])
        for volume in volumes:
            wrapped_command.extend(['-v', volume])

        wrapped_command.extend([self.tag, '/bin/bash', '-c', ' '.join(command)])

        return run_command(wrapped_command, **kwargs)

    def build(self):
        self.containerfile.create_folder_copy_files()
        self.containerfile.prepare_prepended_steps()
        self.containerfile.prepare_galaxy_steps()
        self.containerfile.prepare_introspection_steps()
        print(MessageColors.OK + 'Writing partial Containerfile without collection requirements' + MessageColors.ENDC)
        self.containerfile.write()
        rc, output = run_command(self.build_command, capture_output=True)

        rc, output = self.run_in_container(['introspect', '--write-bindep', '/context/bindep_combined.txt'],
                                           volumes=[f"{os.path.abspath(self.build_context)}:/context:Z"],
                                           capture_output=True)

        collection_data = yaml.safe_load('\n'.join(output))
        if collection_data.get('system'):
            rc, output = self.run_in_container(['bindep', '-b', '-f', '/context/{0}'.format(BINDEP_COMBINED)],
                                               volumes=[f"{os.path.abspath(self.build_context)}:/context:Z"],
                                               allow_error=True, capture_output=True)
            self.containerfile.prepare_system_steps(bindep_output=output)

        self.containerfile.prepare_pip_steps(collection_pip=collection_data['python'])
        self.containerfile.prepare_appended_steps()
        print(MessageColors.OK + 'Rewriting Containerfile to capture collection requirements' + MessageColors.ENDC)
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

    def get_dep(self, entry):
        """Returns the filename of the file within the build context.
        """
        original_path = self.get_dep_abs_path(entry)
        if original_path:
            return os.path.basename(original_path)
        return original_path

    def validate(self):
        bc_files = set(['introspect.py', 'Dockerfile', 'Containerfile'])
        for item in CONTEXT_FILES:
            requirement_path = self.get_dep_abs_path(item)
            if requirement_path:
                filename = os.path.basename(requirement_path)
                if filename in bc_files:
                    raise DefinitionError("Duplicated filename {0} in definition.".format(filename))
                if not os.path.exists(requirement_path):
                    raise DefinitionError("Dependency file {0} does not exist.".format(requirement_path))
                bc_files.add(filename)
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


class Containerfile:
    newline_char = '\n'

    def __init__(self, definition,
                 build_context=constants.default_build_context,
                 base_image=constants.default_base_image,
                 container_runtime=constants.default_container_runtime,
                 tag=constants.default_tag):

        self.build_context = build_context
        self.definition = definition
        filename = constants.runtime_files[container_runtime]
        self.path = os.path.join(self.build_context, filename)
        self.base_image = base_image
        self.container_runtime = container_runtime
        self.tag = tag
        self.steps = [
            "FROM {0}".format(self.base_image),
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

    def prepare_introspection_steps(self):
        source = ansible_builder.introspect.__file__
        dest = os.path.join(self.build_context, 'introspect.py')
        copy_file(source, dest)

        user_files = {'python': None, 'system': None}
        for item, context_name in CONTEXT_FILES.items():
            if self.definition.get_dep_abs_path(item):
                user_files[item] = context_name

        self.steps.extend(
            IntrospectionSteps(
                'introspect.py', user_files['python'], user_files['system'],
                BINDEP_COMBINED
            )
        )

    def prepare_galaxy_steps(self):
        if self.definition.get_dep_abs_path('galaxy'):
            self.steps.extend(GalaxySteps(CONTEXT_FILES['galaxy']))
        return self.steps

    def prepare_pip_steps(self, collection_pip):
        pip_list = sanitize_requirements(collection_pip)

        if ''.join(pip_list).strip():  # only use file if it is non-blank
            pip_file = os.path.join(self.build_context, PIP_COMBINED)
            write_file(pip_file, pip_list)
            self.steps.extend(PipSteps(PIP_COMBINED))

        return self.steps

    def prepare_system_steps(self, bindep_output):
        if ''.join(bindep_output).strip():
            system_file = os.path.join(self.build_context, BINDEP_OUTPUT)
            write_file(system_file, bindep_output)
            self.steps.extend(BindepSteps(BINDEP_OUTPUT))

        return self.steps

    def write(self):
        with open(self.path, 'w') as f:
            for step in self.steps:
                f.write(step + self.newline_char)

        return True
