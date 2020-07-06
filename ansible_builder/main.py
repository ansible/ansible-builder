import os
import yaml
import subprocess
import sys
from shutil import copy

from . import constants


class AnsibleBuilder:
    def __init__(self, action=None,
                 filename=constants.default_file,
                 base_image=constants.default_base_image,
                 build_context=constants.default_build_context,
                 tag=constants.default_tag,
                 container_runtime=constants.default_container_runtime):
        self.action = action
        self.definition = Definition(filename=filename)
        self.base_image = base_image
        self.tag = tag
        self.build_context = build_context
        self.container_runtime = container_runtime
        self.containerfile = Containerfile(
            filename=constants.runtime_files[self.container_runtime],
            definition=self.definition,
            base_image=base_image,
            build_context=self.build_context)

    @property
    def version(self):
        return self.definition.version

    def create(self):
        return self.containerfile.write()

    def build_command(self):
        self.create()
        command = [self.container_runtime, "build"]
        arguments = ["-f", self.containerfile.path,
                     "-t", self.tag,
                     self.build_context]
        command.extend(arguments)
        return command

    def build(self):
        command = self.build_command()
        result = subprocess.run(command)
        if result.returncode == 0:
            return True


class Definition:
    def __init__(self, *args, filename):
        self.filename = filename

        try:
            with open(filename, 'r') as f:
                self.raw = yaml.load(f)
        except FileNotFoundError:
            sys.exit("""
            Could not detect 'execution-environment.yml' file in this directory.
            Use -f to specify a different location.
            """)

    @property
    def version(self):
        version = self.raw.get('version')

        if not version:
            raise ValueError("Expected top-level 'version' key to be present.")

        return str(version)

    @property
    def galaxy_requirements_file(self):
        galaxy_file = self.raw.get('dependencies', {}).get('galaxy')
        if galaxy_file is None or os.path.isabs(galaxy_file):
            return galaxy_file
        else:
            return os.path.join(os.path.dirname(self.filename), galaxy_file)


class Containerfile:
    newline_char = '\n'

    def __init__(self, definition,
                 filename=constants.default_file,
                 build_context=constants.default_build_context,
                 base_image=constants.default_base_image):

        self.build_context = build_context
        os.makedirs(self.build_context, exist_ok=True)
        self.definition = definition
        self.path = os.path.join(self.build_context, filename)
        self.base_image = base_image
        self.build_steps()

    def build_steps(self):
        self.steps = []
        self.steps.append("FROM {}".format(self.base_image))
        self.steps.append(self.newline_char)
        [self.steps.append(step) for step in GalaxySteps(containerfile=self)]

        return self.steps

    def write(self):
        with open(self.path, 'w') as f:
            for step in self.steps:
                if step == self.newline_char:
                    f.write(step)
                else:
                    f.write(step + self.newline_char)

        return True


class GalaxySteps:
    def __new__(cls, *args, containerfile):
        definition = containerfile.definition
        if not definition.galaxy_requirements_file:
            return []
        src = definition.galaxy_requirements_file
        dest = containerfile.build_context
        copy(src, dest)
        basename = os.path.basename(definition.galaxy_requirements_file)
        return [
            "ADD {} /build/".format(basename),
            "RUN ansible-galaxy role install -r /build/{} --roles-path /usr/share/ansible/roles".format(basename),
            "RUN ansible-galaxy collection install -r /build/{} --collections-path /usr/share/ansible/collections".format(basename)
        ]
