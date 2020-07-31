#!/usr/bin/env python3

import os
import re
import sys
import yaml
import argparse


base_collections_path = '/usr/share/ansible/collections'
default_file = 'execution-environment.yml'

begin_delimiter = '----begin_introspect_output----'
end_delimiter = '----end_introspect_output----'


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


def process(data_dir=base_collections_path, user_pip=None, user_bindep=None):
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
        CD = CollectionDefinition(path)
        namespace, name = CD.namespace_name()
        key = '{}.{}'.format(namespace, name)

        py_file = CD.get_dependency('python')
        if py_file:
            col_pip_lines = pip_file_data(os.path.join(path, py_file))
            if col_pip_lines:
                py_req[key] = col_pip_lines

        sys_file = CD.get_dependency('system')
        if sys_file:
            col_sys_lines = bindep_file_data(os.path.join(path, sys_file))
            if col_sys_lines:
                sys_req[key] = col_sys_lines

    # add on entries from user files, if they are given
    if user_pip:
        col_pip_lines = pip_file_data(user_pip)
        if col_pip_lines:
            py_req['user'] = col_pip_lines
    if user_bindep:
        col_sys_lines = bindep_file_data(user_bindep)
        if col_sys_lines:
            sys_req['user'] = col_sys_lines

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


def write_files(data, write_pip=None, write_bindep=None):
    if write_pip and data.get('python'):
        with open(write_pip, 'w') as f:
            f.write('\n'.join(simple_combine(data.get('python')) + ['']))
    if write_bindep and data.get('system'):
        with open(write_bindep, 'w') as f:
            f.write('\n'.join(simple_combine(data.get('system')) + ['']))


def parse_introspect_output(stdout):
    p = re.compile(
        '{0}(?P<yaml_text>.+){1}'.format(begin_delimiter, end_delimiter),
        flags=re.MULTILINE | re.DOTALL
    )
    m = p.search(stdout)
    if m is None:
        return None
    yaml_text = m.group('yaml_text').strip()
    data = yaml.safe_load(yaml_text)
    return data


def add_introspect_options(parser):
    parser.add_argument(
        'folder', default=base_collections_path, nargs='?',
        help=(
            'Ansible collections path(s) to introspect. '
            'This should have a folder named ansible_collections inside of it.'
        )
    )
    parser.add_argument(
        '--user-pip', dest='user_pip',
        help='An additional file to combine with collection pip requirements.'
    )
    parser.add_argument(
        '--user-bindep', dest='user_bindep',
        help='An additional file to combine with collection bindep requirements.'
    )
    parser.add_argument(
        '--write-pip', dest='write_pip',
        help='Write the combined bindep file to this location.'
    )
    parser.add_argument(
        '--write-bindep', dest='write_bindep',
        help='Write the combined bindep file to this location.'
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
    data = process(args.folder, user_pip=args.user_pip, user_bindep=args.user_bindep)
    print(begin_delimiter)
    print(yaml.dump(data, default_flow_style=False))
    print(end_delimiter)
    write_files(data, write_pip=args.write_pip, write_bindep=args.write_bindep)
    sys.exit(0)
