import tempfile
import os
import atexit
import shutil

from .utils import run_command


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
        if self.installed or self.requirements_file is None:
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
