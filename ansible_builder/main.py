import os
import yaml
import subprocess
import sys
import shutil
import tempfile
import atexit

from . import constants
from .steps.galaxy import GalaxySteps
from .steps.pip import PipSteps


def run_command(command):
    print('Running command:')
    print('  {0}'.format(' '.join(command)))
    result = subprocess.run(command)
    return bool(result.returncode == 0)


class CollectionManager:
    def __init__(self, requirements_file, custom_path=None, installed=True):
        self.requirements_file = requirements_file
        if custom_path:
            self._dir = custom_path
            self.installed = installed
        else:
            self._dir = None
            self.installed = False

    @property
    def dir(self):
        if self._dir is None:
            self._dir = tempfile.mkdtemp(prefix='ansible_builder_')
            print('Using temporary directory to obtain collection information:')
            print('  {}'.format(self._dir))
            atexit.register(shutil.rmtree, self._dir)
        return self._dir

    def ensure_installed(self):
        if self.installed:
            return
        run_command([
            'ansible-galaxy', 'collection', 'install',
            '-r', self.requirements_file,
            '-p', self.dir
        ])
        self.installed = True

    def path_list(self):
        self.ensure_installed()
        paths = []
        path_root = os.path.join(self.dir, 'ansible_collections')
        if not os.path.exists(path_root):
            # add debug statements at points like this
            return paths
        for namespace in sorted(os.listdir(path_root)):
            for name in sorted(os.listdir(os.path.join(path_root, namespace))):
                collection_dir = os.path.join(path_root, namespace, name)
                files_list = os.listdir(collection_dir)
                if 'galaxy.yml' in files_list or 'MANIFEST.json' in files_list:
                    paths.append(collection_dir)
        return paths


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
            build_context=self.build_context)

    @property
    def version(self):
        return self.definition.version

    def create(self):
        self.containerfile.build_steps()
        return self.containerfile.write()

    def build_command(self):
        return [
            self.container_runtime, "build",
            "-f", self.containerfile.path,
            "-t", self.tag,
            self.build_context
        ]

    def build(self):
        self.create()
        return run_command(self.build_command())


class BaseDefinition:

    def __init__(self, some_path):
        """Subclasses should populate self.raw in this method"""
        self.raw = {
            'version': 1,
            'dependencies': {}
        }
        self.reference_path = some_path

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
        super(CollectionDefinition, self).__init__(collection_path)
        meta_file = os.path.join(collection_path, 'meta', constants.default_file)
        if os.path.exists(meta_file):
            with open(meta_file, 'r') as f:
                self.raw = yaml.load(f)
        else:
            # A feature? Automatically infer requirements for collection
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

    @property
    def python_requirements_relpath(self):
        req_file = self.raw.get('dependencies', {}).get('python')
        if req_file is None:
            return None
        elif os.path.isabs(req_file):
            raise RuntimeError(
                'Collections must specify relative paths for requirements files. '
                'The file {0} specified by {1} violates this.'.format(
                    req_file, self.reference_path
                )
            )
        else:
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

        self.manager = CollectionManager(self.galaxy_requirements_file)

    def _get_dep_entry(self, entry):
        deps = self.raw.get('dependencies', {})
        req_file = deps.get(entry) if deps else None

        if not req_file:
            return None

        if os.path.isabs(req_file):
            return req_file

        return os.path.join(self.reference_path, req_file)

    @property
    def python_requirements_file(self):
        return self._get_dep_entry('python')

    @property
    def system_requirements_file(self):
        return self._get_dep_entry('system')

    @property
    def galaxy_requirements_file(self):
        return self._get_dep_entry('galaxy')

    def collection_dependencies(self):
        ret = {'python': [], 'system': []}
        for path in self.manager.path_list():
            CD = CollectionDefinition(path)
            if not CD.python_requirements_relpath:
                continue
            namespace, name = CD.namespace_name()
            ret['python'].append(os.path.join(namespace, name, CD.python_requirements_relpath))
        return ret


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

    def build_steps(self):
        self.steps = [
            "FROM {}".format(self.base_image),
            ""
        ]
        self.steps.extend(
            GalaxySteps(containerfile=self)
        )

        # There probably needs to be an intermidiate step here
        # where we introspect the results of running the "galaxy steps"
        # inside of the base image.
        self.steps.extend(
            PipSteps(containerfile=self)
        )

        return self.steps

    def write(self):
        with open(self.path, 'w') as f:
            for step in self.steps:
                f.write(step + self.newline_char)

        return True
