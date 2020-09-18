#!/usr/bin/env python3

import os
import sys
import yaml
import argparse


base_collections_path = '/usr/share/ansible/collections'
default_file = 'execution-environment.yml'


def line_is_empty(line):
    return bool((not line.strip()) or line.startswith('#'))


def pip_file_data(path):
    with open(path, 'r') as f:
        pip_content = f.read()

    pip_lines = []
    for line in pip_content.split('\n'):
        if line_is_empty(line):
            continue
        if line.startswith('-r') or line.startswith('--requirement'):
            _, new_filename = line.split(None, 1)
            new_path = os.path.join(os.path.dirname(path or '.'), new_filename)
            pip_lines.extend(pip_file_data(new_path))
        else:
            pip_lines.append(line)

    return pip_lines


def bindep_file_data(path):
    with open(path, 'r') as f:
        sys_content = f.read()

    sys_lines = []
    for line in sys_content.split('\n'):
        if line_is_empty(line):
            continue
        sys_lines.append(line)

    return sys_lines


def process_collection(path):
    """Return a tuple of (python_dependencies, system_dependencies) for the
    collection install path given.
    Both items returned are a list of dependencies.

    :param str path: root directory of collection (this would contain galaxy.yml file)
    """
    CD = CollectionDefinition(path)

    py_file = CD.get_dependency('python')
    pip_lines = []
    if py_file:
        pip_lines = pip_file_data(os.path.join(path, py_file))

    sys_file = CD.get_dependency('system')
    bindep_lines = []
    if sys_file:
        bindep_lines = bindep_file_data(os.path.join(path, sys_file))

    return (pip_lines, bindep_lines)


def process(data_dir=base_collections_path):
    paths = []
    path_root = os.path.join(data_dir, 'ansible_collections')

    # build a list of all the valid collection paths
    if os.path.exists(path_root):
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

    # populate the requirements content
    py_req = {}
    sys_req = {}
    for path in paths:
        col_pip_lines, col_sys_lines = process_collection(path)
        CD = CollectionDefinition(path)
        namespace, name = CD.namespace_name()
        key = '{}.{}'.format(namespace, name)

        if col_pip_lines:
            py_req[key] = col_pip_lines

        if col_sys_lines:
            sys_req[key] = col_sys_lines

    return {
        'python': py_req,
        'system': sys_req
    }


def has_content(candidate_file):
    """Beyond checking that the candidate exists, this also assures
    that the file has something other than whitespace,
    which can cause errors when given to pip.
    """
    if not os.path.exists(candidate_file):
        return False
    with open(candidate_file, 'r') as f:
        content = f.read()
    return bool(content.strip().strip('\n'))


class CollectionDefinition:
    """This class represents the dependency metadata for a collection
    should be replaced by logic to hit the Galaxy API if made available
    """

    def __init__(self, collection_path):
        self.reference_path = collection_path
        meta_file = os.path.join(collection_path, 'meta', default_file)
        if os.path.exists(meta_file):
            with open(meta_file, 'r') as f:
                self.raw = yaml.safe_load(f)
        else:
            self.raw = {'version': 1, 'dependencies': {}}
            # Automatically infer requirements for collection
            for entry, filename in [('python', 'requirements.txt'), ('system', 'bindep.txt')]:
                candidate_file = os.path.join(collection_path, filename)
                if has_content(candidate_file):
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


def simple_combine(reqs):
    """Given a dictionary of requirement lines keyed off collections,
    return a list with the most basic of de-duplication logic,
    and comments indicating the sources based off the collection keys
    """
    consolidated = []
    fancy_lines = []
    for collection, lines in reqs.items():
        for line in lines:
            if line_is_empty(line):
                continue

            base_line = line.split('#')[0].strip()
            if base_line in consolidated:
                i = consolidated.index(base_line)
                fancy_lines[i] += ', {}'.format(collection)
            else:
                fancy_line = base_line + '  # from collection {}'.format(collection)
                consolidated.append(base_line)
                fancy_lines.append(fancy_line)

    return fancy_lines


def add_introspect_options(parser):
    parser.add_argument(
        'folder', default=base_collections_path, nargs='?',
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
    data = process(args.folder)
    print(yaml.dump(data, default_flow_style=False))
    sys.exit(0)
