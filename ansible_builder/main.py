import os
import yaml
import sys
import shutil
import filecmp
import textwrap

from . import constants
from .colors import MessageColors
from .steps import AdditionalBuildSteps, GalaxySteps, PipSteps, IntrospectionSteps
from .utils import run_command
import ansible_builder.introspect


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
            filename=constants.runtime_files[self.container_runtime],
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

    def build(self):
        self.containerfile.prepare_prepended_steps()
        self.containerfile.prepare_introspection_steps()
        self.containerfile.prepare_galaxy_steps()
        print(MessageColors.OK + 'Writing partial Containerfile without collection requirements' + MessageColors.ENDC)
        self.containerfile.write()
        run_command(self.build_command)
        self.containerfile.prepare_pip_steps()
        print(MessageColors.OK + 'Rewriting Containerfile to capture collection requirements' + MessageColors.ENDC)
        self.containerfile.prepare_appended_steps()
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
                y = yaml.load(f)
                self.raw = y if y else {}
        except FileNotFoundError:
            sys.exit(MessageColors.FAIL + """
            Could not detect '{0}' file in this directory.
            Use -f to specify a different location.
            """.format(constants.default_file) + MessageColors.ENDC)
        except yaml.parser.ParserError as e:
            sys.exit(MessageColors.FAIL + textwrap.dedent("""
            An error occured while parsing the definition file:
            {0}
            """).format(str(e)) + MessageColors.ENDC)

    def get_additional_commands(self):
        """Gets additional commands from the exec env file, if any are specified.
        """
        commands = self.raw.get('additional_build_steps')
        return commands

    def get_dependency(self, entry):
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


class Containerfile:
    newline_char = '\n'

    def __init__(self, definition,
                 filename=constants.default_file,
                 build_context=constants.default_build_context,
                 base_image=constants.default_base_image,
                 container_runtime=constants.default_container_runtime,
                 tag=constants.default_tag):

        self.build_context = build_context
        os.makedirs(self.build_context, exist_ok=True)
        self.definition = definition
        self.path = os.path.join(self.build_context, filename)
        self.base_image = base_image
        self.container_runtime = container_runtime
        self.tag = tag
        self.steps = [
            "FROM {}".format(self.base_image),
            ""
        ]

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
        exists = os.path.exists(dest)
        if not exists or not filecmp.cmp(source, dest, shallow=False):
            shutil.copy(source, dest)

        self.steps.extend(IntrospectionSteps(os.path.basename(dest)))

    def prepare_galaxy_steps(self):
        galaxy_requirements_path = self.definition.get_dependency('galaxy')
        if galaxy_requirements_path:
            # name is most likely "requirements.yml"
            galaxy_requirements_name = os.path.basename(galaxy_requirements_path)
            # TODO: what if build context file exists? https://github.com/ansible/ansible-builder/issues/20
            dest = os.path.join(self.build_context, galaxy_requirements_name)
            exists = os.path.exists(dest)
            if not exists or not filecmp.cmp(galaxy_requirements_path, dest, shallow=False):
                shutil.copy(galaxy_requirements_path, dest)

            self.steps.extend(GalaxySteps(galaxy_requirements_name))

    def prepare_pip_steps(self):
        python_req_path = self.definition.get_dependency('python')
        if python_req_path:
            shutil.copy(python_req_path, self.build_context)


        command = [self.container_runtime, "run", "--rm", self.tag, "introspect"]
        rc, output = run_command(command, capture_output=True)
        if rc != 0:
            print(MessageColors.WARNING + 'No collections requirements file found, skipping ansible-galaxy install...' + MessageColors.ENDC)
            requirements_files = []
        else:
            requirements_files = yaml.load("\n".join(output)) or []

        self.steps.extend(
            PipSteps(
                python_req_path,
                requirements_files
            )
        )

        return self.steps

    def write(self):
        with open(self.path, 'w') as f:
            for step in self.steps:
                f.write(step + self.newline_char)

        return True
