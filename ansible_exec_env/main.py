import os
import yaml
from shutil import copy


default_base_image = 'shanemcd/ansible-runner'


class AnsibleExecEnv:
    def __init__(self, filename='execution-environment.yml', base_image=default_base_image, build_context=None):
        self.definition = Definition(filename=filename)
        self.base_image = base_image
        self.build_context = build_context or os.path.join(os.getcwd(), 'context')
        self.containerfile = Containerfile(
            filename='Containerfile',
            definition=self.definition,
            base_image=base_image,
            build_context=self.build_context)

    @property
    def version(self):
        return self.definition.version

    def process(self):
        return self.containerfile.write()


class Definition:
    def __init__(self, *args, filename):
        self.filename = filename

        with open(filename, 'r') as f:
            self.raw = yaml.load(f, Loader=yaml.FullLoader)

    @property
    def version(self):
        version = self.raw.get('version')

        if not version:
            raise ValueError("Expected top-level 'version' key to be present.")

        return str(version)

    @property
    def galaxy_requirements_file(self):
        return self.raw.get('dependencies', {}).get('galaxy')


class Containerfile:
    newline_char = '\n'

    def __init__(self, *args, filename, definition, build_context, base_image):
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
            "RUN ansible-galaxy collection install -r /build/{}".format(basename)
        ]
