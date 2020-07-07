import tempfile
import os
import atexit
import shutil

from .utils import run_command


class CollectionManager:
    def __init__(self, dir, requirements_file=None, installed=True):
        self.dir = dir
        self.requirements_file = requirements_file
        self.installed = installed

    @classmethod
    def from_directory(cls, custom_path):
        return cls(custom_path, installed=True)

    @classmethod
    def from_requirements(cls, requirements_file):
        dir = tempfile.mkdtemp(prefix='ansible_builder_')
        print('Using temporary directory to obtain collection information:')
        print('  {}'.format(dir))
        atexit.register(shutil.rmtree, dir)
        return cls(dir, requirements_file=requirements_file, installed=False)

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
