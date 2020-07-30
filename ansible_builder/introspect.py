#!/usr/bin/env python3

import os
import sys
import yaml
import argparse


base_collections_path = '/usr/share/ansible/collections'
default_file = 'execution-environment.yml'


def pip_file_data(path):
    req_list = []
    with open(path, 'r') as f:
        for line in f.read().split('\n'):
            if not line:
                continue
            if line.startswith('-r') or line.startswith('--requirement'):
                _, new_filename = line.split(None, 1)
                new_path = os.path.join(os.path.dirname(path or '.'), new_filename)
                req_list.extend(pip_file_data(new_path))
            else:
                req_list.append(line)
    return req_list


def process(data_dir=base_collections_path):
    paths = []
    path_root = os.path.join(data_dir, 'ansible_collections')
    if not os.path.exists(path_root):
        return {'python': [], 'system': []}

    for namespace in sorted(os.listdir(path_root)):
        if not os.path.isdir(os.path.join(path_root, namespace)):
            continue
        for name in sorted(os.listdir(os.path.join(path_root, namespace))):
            collection_dir = os.path.join(path_root, namespace, name)
            if not os.path.isdir(collection_dir):
                continue
            files_list = os.listdir(collection_dir)
            if 'galaxy.yml' in files_list or 'MANIFEST.json' in files_list:
                paths.append(collection_dir)

    py_req = []
    sys_req = []
    for path in paths:
        CD = CollectionDefinition(path)
        namespace, name = CD.namespace_name()

        py_file = CD.get_dependency('python')
        if py_file:
            py_req.extend(
                pip_file_data(os.path.join(path, py_file))
            )

        sys_file = CD.get_dependency('system')
        if sys_file:
            sys_req.append(os.path.join(namespace, name, sys_file))

    return {
        'python': py_req,
        'system': sys_req
    }


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


def add_introspect_options(parser):
    parser.add_argument(
        'folders', default=[base_collections_path], nargs='*',
        help=(
            'Ansible collections path(s) to introspect. '
            'This should have a folder named ansible_collections inside of it.'
        )
    )


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        prog='ansible-builder-introspector',
        description=(
            'This is for programmatic use. '
            'Use ansible-builder introspect instead.'
        )
    )
    add_introspect_options(parser)
    args = parser.parse_args()
    # TODO: modify contract to handle multiple locations more gracefully
    data = {'python': [], 'system': []}
    for folder in args.folders:
        this_data = process(folder)
        data['python'].extend(this_data['python'])
        data['system'].extend(this_data['system'])
    print(yaml.dump(data, default_flow_style=False))
    sys.exit(0)
