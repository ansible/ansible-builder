import os
import yaml
import sys
import shutil
import filecmp

from . import constants
from .steps import GalaxySteps, PipSteps
from .utils import run_command


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
        self.containerfile.prepare_galaxy_steps()
        self.containerfile.write()
        run_command(self.build_command)
        self.containerfile.prepare_pip_steps()
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


class CollectionDefinition(BaseDefinition):
    """This class represents the dependency metadata for a collection
    should be replaced by logic to hit the Galaxy API if made available
    """

    def __init__(self, collection_path):
        self.reference_path = collection_path
        meta_file = os.path.join(collection_path, 'meta', constants.default_file)
        if os.path.exists(meta_file):
            with open(meta_file, 'r') as f:
                self.raw = yaml.load(f)
        else:
            self.raw = {'version': 1, 'dependencies': {}}
            # Automatically infer requirements for collection
            for entry, filename in [('python', 'requirements.txt'), ('system', 'bindep.txt')]:
                candidate_file = os.path.join(collection_path, filename)
                if os.path.exists(candidate_file):
                    self.raw['dependencies'][entry] = filename

    def target_dir(self):
        namespace, name = self.namespace_name()
        return os.path.join(
            constants.base_collections_path, 'ansible_collections',
            namespace, name
        )

    def namespace_name(self):
        "Returns 2-tuple of namespace and name"
        path_parts = [p for p in self.reference_path.split(os.path.sep) if p]
        return tuple(path_parts[-2:])

    def get_dependency(self, entry):
        """A collection is only allowed to reference a file by a relative path
        which is relative to the collection root
        """
        req_file = self.raw.get('dependencies', {}).get(entry)
        if req_file is None:
            return None
        elif os.path.isabs(req_file):
            raise RuntimeError(
                'Collections must specify relative paths for requirements files. '
                'The file {0} specified by {1} violates this.'.format(
                    req_file, self.reference_path
                )
            )

        return req_file


class UserDefinition(BaseDefinition):
    def __init__(self, filename):
        self.filename = filename
        self.reference_path = os.path.dirname(filename)

        try:
            with open(filename, 'r') as f:
                y = yaml.load(f)
                self.raw = y if y else {}
        except FileNotFoundError:
            sys.exit("""
            Could not detect '{0}' file in this directory.
            Use -f to specify a different location.
            """.format(constants.default_file))

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
        self.steps = []

    def prepare_galaxy_steps(self):
        self.steps = [
            "FROM {}".format(self.base_image),
            ""
        ]
        galaxy_requirements_path = self.definition.get_dependency('galaxy')
        if galaxy_requirements_path:
            # TODO: what if build context file exists? https://github.com/ansible/ansible-builder/issues/20
            dest = os.path.join(self.build_context, galaxy_requirements_path)
            exists = os.path.exists(dest)
            if not exists or not filecmp.cmp(galaxy_requirements_path, dest, shallow=False):
                shutil.copy(galaxy_requirements_path, dest)

            self.steps.extend(
                GalaxySteps(
                    os.path.basename(galaxy_requirements_path)  # probably "requirements.yml"
                )
            )

    def prepare_pip_steps(self):
        python_req_path = self.definition.get_dependency('python')
        if python_req_path:
            shutil.copy(python_req_path, self.build_context)


        command = [
            self.container_runtime, "run", "--rm", self.tag,
            "ansible-builder", "introspect"
        ]
        rc, output = run_command(command, capture_output=True)

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
