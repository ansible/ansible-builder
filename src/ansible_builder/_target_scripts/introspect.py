import argparse
import logging
import os
import re
import sys
import yaml

base_collections_path = '/usr/share/ansible/collections'
logger = logging.getLogger(__name__)

# https://peps.python.org/pep-0503/#normalized-names
REQ_NORM_RE = re.compile(r'[-_.]+')
REQ_NAME_RE = re.compile(r'^([-\w.]+)')


def line_is_empty(line):
    return bool((not line.strip()) or line.startswith('#'))


def read_req_file(path):
    """Provide some minimal error and display handling for file reading"""
    if not os.path.exists(path):
        print(f'Expected requirements file not present at: {os.path.abspath(path)}')
    with open(path, 'r') as f:
        return f.read()


def pip_file_data(path):
    pip_content = read_req_file(path)

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
    sys_content = read_req_file(path)

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


def process(data_dir=base_collections_path, user_pip=None, user_bindep=None,
            user_pip_exclude=None, user_bindep_exclude=None):
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
        key = f'{namespace}.{name}'

        if col_pip_lines:
            py_req[key] = col_pip_lines

        if col_sys_lines:
            sys_req[key] = col_sys_lines

    # add on entries from user files, if they are given
    if user_pip:
        col_pip_lines = pip_file_data(user_pip)
        if col_pip_lines:
            py_req['user'] = col_pip_lines
    if user_pip_exclude:
        col_pip_exclude_lines = pip_file_data(user_pip_exclude)
        if col_pip_exclude_lines:
            py_req['exclude'] = col_pip_exclude_lines
    if user_bindep:
        col_sys_lines = bindep_file_data(user_bindep)
        if col_sys_lines:
            sys_req['user'] = col_sys_lines
    if user_bindep_exclude:
        col_sys_exclude_lines = bindep_file_data(user_bindep_exclude)
        if col_sys_exclude_lines:
            sys_req['exclude'] = col_sys_exclude_lines

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

        # NOTE: Filenames should match constants.DEAFULT_EE_BASENAME and constants.YAML_FILENAME_EXTENSIONS.
        meta_file_base = os.path.join(collection_path, 'meta', 'execution-environment')
        ee_exists = False
        for ext in ('yml', 'yaml'):
            meta_file = f"{meta_file_base}.{ext}"
            if os.path.exists(meta_file):
                with open(meta_file, 'r') as f:
                    self.raw = yaml.safe_load(f)
                ee_exists = True
                break

        if not ee_exists:
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
        if os.path.isabs(req_file):
            raise RuntimeError(
                'Collections must specify relative paths for requirements files. '
                f'The file {req_file} specified by {self.reference_path} violates this.'
            )

        return req_file


def simple_combine(reqs, exclude=None, name_only=False):
    """Given a dictionary of requirement lines keyed off collections,
    return a list with the most basic of de-duplication logic,
    and comments indicating the sources based off the collection keys
    """
    if exclude is None:
        exclude = []

    consolidated = []
    fancy_lines = []
    for collection, lines in reqs.items():
        for line in lines:
            if line_is_empty(line):
                continue

            base_line = line.split('#')[0].strip()
            name_match = REQ_NAME_RE.match(base_line)
            name = REQ_NORM_RE.sub('-', name_match.group(1))
            if name in exclude and collection not in {'user', 'exclude'}:
                logger.debug('# Explicitly excluding requirement %s from %s', name, collection)
                continue
            if name in EXCLUDE_REQUIREMENTS and collection not in {'user', 'exclude'}:
                logger.debug('# Excluding requirement %s from %s', name, collection)
                continue

            if base_line in consolidated:
                i = consolidated.index(base_line)
                if not name_only:
                    fancy_lines[i] += f', {collection}'
            else:
                if name_only:
                    fancy_line = name
                else:
                    fancy_line = f'{base_line}  # from collection {collection}'
                consolidated.append(base_line)
                fancy_lines.append(fancy_line)

    return fancy_lines


def parse_args(args=None):

    parser = argparse.ArgumentParser(
        prog='introspect',
        description=(
            'ansible-builder introspection; injected and used during execution environment build'
        )
    )

    subparsers = parser.add_subparsers(
        help='The command to invoke.',
        dest='action',
        required=True,
    )

    create_introspect_parser(subparsers)

    return parser.parse_args(args)


def run_introspect(args, log):
    data = process(args.folder, user_pip=args.user_pip, user_bindep=args.user_bindep,
                   user_pip_exclude=args.user_pip_exclude, user_bindep_exclude=args.user_bindep_exclude)
    log.info('# Dependency data for %s', args.folder)
    data['python'] = simple_combine(
        data['python'],
        exclude=simple_combine({'exclude': data['python'].pop('exclude', {})}, name_only=True)
    )
    data['system'] = simple_combine(
        data['system'],
        exclude=simple_combine({'exclude': data['system'].pop('exclude', {})}, name_only=True)
    )

    print('---')
    print(yaml.dump(data, default_flow_style=False))

    if args.write_pip and data.get('python'):
        write_file(args.write_pip, data.get('python') + [''])
    if args.write_bindep and data.get('system'):
        write_file(args.write_bindep, data.get('system') + [''])

    sys.exit(0)


def create_introspect_parser(parser):
    introspect_parser = parser.add_parser(
        'introspect',
        help='Introspects collections in folder.',
        description=(
            'Loops over collections in folder and returns data about dependencies. '
            'This is used internally and exposed here for verification. '
            'This is targeted toward collection authors and maintainers.'
        )
    )
    introspect_parser.add_argument('--sanitize', action='store_true',
                                   help=argparse.SUPPRESS)

    introspect_parser.add_argument(
        'folder', default=base_collections_path, nargs='?',
        help=(
            'Ansible collections path(s) to introspect. '
            'This should have a folder named ansible_collections inside of it.'
        )
    )
    # Combine user requirements and collection requirements into single file
    # in the future, could look into passing multilple files to
    # python-builder scripts to be fed multiple files as opposed to this
    introspect_parser.add_argument(
        '--user-pip', dest='user_pip',
        help='An additional file to combine with collection pip requirements.'
    )
    introspect_parser.add_argument(
        '--user-pip-exclude', dest='user_pip_exclude',
        help='An additional file to exclude specific pip requirements.'
    )
    introspect_parser.add_argument(
        '--user-bindep', dest='user_bindep',
        help='An additional file to combine with collection bindep requirements.'
    )
    introspect_parser.add_argument(
        '--user-bindep-exclude', dest='user_bindep_exclude',
        help='An additional file to exclude specific bindep requirements.'
    )
    introspect_parser.add_argument(
        '--write-pip', dest='write_pip',
        help='Write the combined pip requirements file to this location.'
    )
    introspect_parser.add_argument(
        '--write-bindep', dest='write_bindep',
        help='Write the combined bindep requirements file to this location.'
    )

    return introspect_parser


EXCLUDE_REQUIREMENTS = frozenset((
    # obviously already satisfied or unwanted
    'ansible', 'ansible-base', 'python', 'ansible-core',
    # general python test requirements
    'tox', 'pycodestyle', 'yamllint', 'pylint',
    'flake8', 'pytest', 'pytest-xdist', 'coverage', 'mock', 'testinfra',
    # test requirements highly specific to Ansible testing
    'ansible-lint', 'molecule', 'galaxy-importer', 'voluptuous',
    # already present in image for py3 environments
    'yaml', 'pyyaml', 'json',
))


def write_file(filename: str, lines: list) -> bool:
    parent_dir = os.path.dirname(filename)
    if parent_dir and not os.path.exists(parent_dir):
        logger.warning('Creating parent directory for %s', filename)
        os.makedirs(parent_dir)
    new_text = '\n'.join(lines)
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            if f.read() == new_text:
                logger.debug("File %s is already up-to-date.", filename)
                return False
            logger.warning('File %s had modifications and will be rewritten', filename)
    with open(filename, 'w') as f:
        f.write(new_text)
    return True


def main():
    args = parse_args()

    if args.action == 'introspect':
        run_introspect(args, logger)

    logger.error("An error has occurred.")
    sys.exit(1)


if __name__ == '__main__':
    main()
