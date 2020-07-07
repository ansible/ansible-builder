import os
import yaml
import sys
import shutil

from . import constants
from .steps import GalaxySteps, PipSteps
from .collections import CollectionManager
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

        self.manager = CollectionManager.from_requirements(self.get_dependency('galaxy'))

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

    def collection_dependencies(self, dep_type='python'):
        """Returns a list of files for the dependency type
        These are the dependency files declared by collections which
        the user definition listed in its Galaxy requirement file
        in other words, this returns indirect dependencies of given type
        """
        ret = []
        for path in self.manager.path_list():
            CD = CollectionDefinition(path)
            dep_file = CD.get_dependency(dep_type)
            if not dep_file:
                continue
            namespace, name = CD.namespace_name()
            ret.append(os.path.join(namespace, name, dep_file))
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
        requirements_path = self.definition.get_dependency('galaxy')
        if requirements_path:
            # TODO: what if build context file exists? https://github.com/ansible/ansible-builder/issues/20
            shutil.copy(requirements_path, self.build_context)
            self.steps.extend(
                GalaxySteps(
                    os.path.basename(requirements_path)  # probably "requirements.yml"
                )
            )

        # There probably needs to be an intermidiate step here
        # where we introspect the results of running the "galaxy steps"
        # inside of the base image.
        python_req_path = self.definition.get_dependency('python')
        if python_req_path:
            shutil.copy(python_req_path, self.build_context)
        self.steps.extend(
            PipSteps(
                python_req_path,
                self.definition.collection_dependencies()
            )
        )

        return self.steps

    def write(self):
        with open(self.path, 'w') as f:
            for step in self.steps:
                f.write(step + self.newline_char)

        return True
