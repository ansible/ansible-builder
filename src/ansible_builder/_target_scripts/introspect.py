from __future__ import annotations

import argparse
import logging
import os
import re
import sys
import yaml

from packaging.requirements import InvalidRequirement, Requirement


BASE_COLLECTIONS_PATH = '/usr/share/ansible/collections'


# regex for a comment at the start of a line, or embedded with leading space(s)
COMMENT_RE = re.compile(r'(?:^|\s+)#.*$')


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


logger = logging.getLogger(__name__)


class CollectionDefinition:
    """
    This class represents the dependency metadata for a collection
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
            BASE_COLLECTIONS_PATH, 'ansible_collections',
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
    col_def = CollectionDefinition(path)

    py_file = col_def.get_dependency('python')
    pip_lines = []
    if py_file:
        pip_lines = pip_file_data(os.path.join(path, py_file))

    sys_file = col_def.get_dependency('system')
    bindep_lines = []
    if sys_file:
        bindep_lines = bindep_file_data(os.path.join(path, sys_file))

    return (pip_lines, bindep_lines)


def process(data_dir=BASE_COLLECTIONS_PATH,
            user_pip=None,
            user_bindep=None,
            exclude_pip=None,
            exclude_bindep=None,
            exclude_collections=None):
    """
    Build a dictionary of Python and system requirements from any collections
    installed in data_dir, and any user specified requirements.

    Excluded requirements, if any, will be inserted into the return dict.

    Example return dict:
       {
          'python': {
              'collection.a': ['abc', 'def'],
              'collection.b': ['ghi'],
              'user': ['jkl'],
              'exclude: ['abc'],
          },
          'system': {
              'collection.a': ['ZYX'],
              'user': ['WVU'],
              'exclude': ['ZYX'],
          },
          'excluded_collections': [
              'a.b',
          ]
       }
    """
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
        col_def = CollectionDefinition(path)
        namespace, name = col_def.namespace_name()
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
    if exclude_pip:
        col_pip_exclude_lines = pip_file_data(exclude_pip)
        if col_pip_exclude_lines:
            py_req['exclude'] = col_pip_exclude_lines
    if user_bindep:
        col_sys_lines = bindep_file_data(user_bindep)
        if col_sys_lines:
            sys_req['user'] = col_sys_lines
    if exclude_bindep:
        col_sys_exclude_lines = bindep_file_data(exclude_bindep)
        if col_sys_exclude_lines:
            sys_req['exclude'] = col_sys_exclude_lines

    retval = {
        'python': py_req,
        'system': sys_req,
    }

    if exclude_collections:
        # This file should just be a newline separated list of collection names,
        # so reusing bindep_file_data() to read it should work fine.
        excluded_collection_list = bindep_file_data(exclude_collections)
        if excluded_collection_list:
            retval['excluded_collections'] = excluded_collection_list

    return retval


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


def strip_comments(reqs: dict[str, list]) -> dict[str, list]:
    """
    Filter any comments out of the Python collection requirements input.

    :param dict reqs: A dict of Python requirements, keyed by collection name.

    :return: Same as the input parameter, except with no comment lines.
    """
    result: dict[str, list] = {}
    for collection, lines in reqs.items():
        for line in lines:
            # strip comments
            if (base_line := COMMENT_RE.sub('', line.strip())):
                result.setdefault(collection, []).append(base_line)

    return result


def should_be_excluded(value: str, exclusion_list: list[str]) -> bool:
    """
    Test if `value` matches against any value in `exclusion_list`.

    The exclusion_list values are either strings to be compared in a case-insensitive
    manner against value, OR, they are regular expressions to be tested against the
    value. A regular expression will contain '~' as the first character.

    :return: True if the value should be excluded, False otherwise.
    """
    for exclude_value in exclusion_list:
        if exclude_value[0] == "~":
            pattern = exclude_value[1:]
            if re.fullmatch(pattern.lower(), value.lower()):
                return True
        elif exclude_value.lower() == value.lower():
            return True
    return False


def filter_requirements(reqs: dict[str, list],
                        exclude: list[str] | None = None,
                        exclude_collections: list[str] | None = None,
                        is_python: bool = True) -> list[str]:
    """
    Given a dictionary of Python requirement lines keyed off collections,
    return a list of cleaned up (no source comments) requirements
    annotated with comments indicating the sources based off the collection keys.

    Currently, non-pep508 compliant Python entries are passed through. We also no
    longer attempt to normalize names (replace '_' with '-', etc), other than
    lowercasing it for exclusion matching, since we no longer are attempting
    to combine similar entries.

    :param dict reqs: A dict of either Python or system requirements, keyed by collection name.
    :param list exclude: A list of requirements to be excluded from the output.
    :param list exclude_collections: A list of collection names from which to exclude all requirements.
    :param bool is_python: This should be set to True for Python requirements, as each
        will be tested for PEP508 compliance. This should be set to False for system requirements.

    :return: A list of filtered and annotated requirements.
    """
    exclusions: list[str] = []
    collection_ignore_list: list[str] = []

    if exclude:
        exclusions = exclude.copy()
    if exclude_collections:
        collection_ignore_list = exclude_collections.copy()

    annotated_lines: list[str] = []
    uncommented_reqs = strip_comments(reqs)

    for collection, lines in uncommented_reqs.items():
        # Bypass this collection if we've been told to ignore all requirements from it.
        if should_be_excluded(collection, collection_ignore_list):
            logger.debug("# Excluding all requirements from collection '%s'", collection)
            continue

        for line in lines:
            # Determine the simple name based on type of requirement
            if is_python:
                try:
                    parsed_req = Requirement(line)
                    name = parsed_req.name
                except InvalidRequirement:
                    logger.warning(
                        "Passing through non-PEP508 compliant line '%s' from collection '%s'",
                        line, collection
                    )
                    annotated_lines.append(line)  # We intentionally won't annotate these lines (multi-line?)
                    continue
            else:
                # bindep system requirements have the package name as the first "word" on the line
                name = line.split(maxsplit=1)[0]

            if collection.lower() not in {'user', 'exclude'}:
                lower_name = name.lower()

                if lower_name in EXCLUDE_REQUIREMENTS:
                    logger.debug("# Excluding requirement '%s' from '%s'", name, collection)
                    continue

                if should_be_excluded(lower_name, exclusions):
                    logger.debug("# Explicitly excluding requirement '%s' from '%s'", name, collection)
                    continue

            annotated_lines.append(f'{line}  # from collection {collection}')

    return annotated_lines


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
    data = process(args.folder,
                   user_pip=args.user_pip,
                   user_bindep=args.user_bindep,
                   exclude_pip=args.exclude_pip,
                   exclude_bindep=args.exclude_bindep,
                   exclude_collections=args.exclude_collections)
    log.info('# Dependency data for %s', args.folder)

    excluded_collections = data.pop('excluded_collections', None)

    data['python'] = filter_requirements(
        data['python'],
        exclude=data['python'].pop('exclude', []),
        exclude_collections=excluded_collections,
    )

    data['system'] = filter_requirements(
        data['system'],
        exclude=data['system'].pop('exclude', []),
        exclude_collections=excluded_collections,
        is_python=False
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
        'folder', default=BASE_COLLECTIONS_PATH, nargs='?',
        help=(
            'Ansible collections path(s) to introspect. '
            'This should have a folder named ansible_collections inside of it.'
        )
    )

    introspect_parser.add_argument(
        '--user-pip', dest='user_pip',
        help='An additional file to combine with collection pip requirements.'
    )
    introspect_parser.add_argument(
        '--user-bindep', dest='user_bindep',
        help='An additional file to combine with collection bindep requirements.'
    )
    introspect_parser.add_argument(
        '--exclude-bindep-reqs', dest='exclude_bindep',
        help='An additional file to exclude specific bindep requirements from collections.'
    )
    introspect_parser.add_argument(
        '--exclude-pip-reqs', dest='exclude_pip',
        help='An additional file to exclude specific pip requirements from collections.'
    )
    introspect_parser.add_argument(
        '--exclude-collection-reqs', dest='exclude_collections',
        help='An additional file to exclude all requirements from the listed collections.'
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
