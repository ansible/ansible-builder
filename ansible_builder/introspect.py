#!/usr/bin/env python3

import os
import sys
import yaml

base_collections_path = '/usr/share/ansible/collections'
default_file = 'execution-environment.yml'


def process(data_dir=base_collections_path):
    paths = []
    path_root = os.path.join(data_dir, 'ansible_collections')
    if not os.path.exists(path_root):
        # add debug statements at points like this
        sys.exit(1)

    for namespace in sorted(os.listdir(path_root)):
        if not os.path.isdir(os.path.join(path_root, namespace)):
            continue
        for name in sorted(os.listdir(os.path.join(path_root, namespace))):
            if not os.path.isdir(os.path.join(path_root, namespace, name)):
                continue
            collection_dir = os.path.join(path_root, namespace, name)
            files_list = os.listdir(collection_dir)
            if 'galaxy.yml' in files_list or 'MANIFEST.json' in files_list:
                paths.append(collection_dir)

    ret = []
    for path in paths:
        CD = CollectionDefinition(path)
        dep_file = CD.get_dependency('python')
        if not dep_file:
            continue
        namespace, name = CD.namespace_name()
        ret.append(os.path.join(namespace, name, dep_file))

    return ret


class CollectionDefinition:
    """This class represents the dependency metadata for a collection
    should be replaced by logic to hit the Galaxy API if made available
    """

    def __init__(self, collection_path):
        self.reference_path = collection_path
        meta_file = os.path.join(collection_path, 'meta', default_file)
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
            base_collections_path, 'ansible_collections',
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


if __name__ == '__main__':
    print(yaml.dump(process(), default_flow_style=False))
    sys.exit(0)
