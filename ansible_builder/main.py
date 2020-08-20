import os
import textwrap
import yaml

from . import constants
from .colors import MessageColors
from .exceptions import DefinitionError
from .steps import AdditionalBuildSteps, GalaxySteps, PipSteps, BindepSteps
from .utils import run_command, write_file, copy_file
from .requirements import sanitize_requirements
import ansible_builder.introspect


# Files that need to be moved into the build context, and their naming inside the context
CONTEXT_FILES = {
    'galaxy': 'requirements.yml'
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

        wrapped_command.extend(['-v', f"{os.path.abspath(self.build_context)}:/context:Z"])

        wrapped_command.extend([self.tag, '/bin/bash', '-c', ' '.join(command)])

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

        bindep_output = []
        if system_lines:
            write_file(os.path.join(self.build_context, BINDEP_COMBINED), system_lines + [''])

            rc, bindep_output = self.run_in_container(
                ['bindep', '-b', '-f', '/context/{0}'.format(BINDEP_COMBINED)],
                allow_error=True, capture_output=True
            )

        return (bindep_output, python_lines)

    def build(self):
        # Phase 1 of Containerfile
        self.containerfile.create_folder_copy_files()
        self.containerfile.prepare_prepended_steps()
        self.containerfile.prepare_galaxy_steps()
        print(MessageColors.OK + 'Writing partial Containerfile without collection requirements' + MessageColors.ENDC)
        self.containerfile.write()

        system_lines, pip_lines = self.run_intermission()

        # Phase 2 of Containerfile
        self.containerfile.prepare_system_steps(bindep_output=system_lines)
        self.containerfile.prepare_pip_steps(pip_lines=pip_lines)
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
        for item in CONTEXT_FILES:
            requirement_path = self.get_dep_abs_path(item)
            if requirement_path:
                if not os.path.exists(requirement_path):
                    raise DefinitionError("Dependency file {0} does not exist.".format(requirement_path))

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

        # copy introspect.py file from source into build context
        copy_file(
            ansible_builder.introspect.__file__,
            os.path.join(self.build_context, 'introspect.py')
        )

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

    def prepare_galaxy_steps(self):
        if self.definition.get_dep_abs_path('galaxy'):
            self.steps.extend(GalaxySteps(CONTEXT_FILES['galaxy']))
        return self.steps

    def prepare_pip_steps(self, pip_lines):
        if ''.join(pip_lines).strip():  # only use file if it is non-blank
            pip_file = os.path.join(self.build_context, PIP_COMBINED)
            write_file(pip_file, pip_lines)
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
