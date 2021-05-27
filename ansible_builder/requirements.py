import logging

# python requirements-parser
import requirements

# bindep is available as CLI, but this interface gives us extra information
from bindep.depends import Depends


logger = logging.getLogger(__name__)

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


def sanitize_python_requirements(collection_py_reqs):
    # de-duplication
    consolidated = []
    seen_pkgs = set()
    for collection, lines in collection_py_reqs.items():
        try:
            for req in requirements.parse('\n'.join(lines)):
                req.collections = [collection]  # add backref for later
                if req.name is None:
                    consolidated.append(req)
                    continue
                if req.name in seen_pkgs:
                    for prior_req in consolidated:
                        if req.name == prior_req.name:
                            prior_req.specs.extend(req.specs)
                            prior_req.collections.append(collection)
                            break
                    continue
                consolidated.append(req)
                seen_pkgs.add(req.name)
        except Exception as e:
            raise RuntimeError(
                'Failed to parse system requirement from {}, lines: \n{}\nerror: \n{}'.format(
                    collection, lines, str(e)
                ))

    # removal of unwanted packages
    sanitized = []
    for req in consolidated:
        if req.name and req.name.lower() in EXCLUDE_REQUIREMENTS:
            logger.debug(f'# Excluding requirement {req.name} from {req.collections}')
            continue
        if req.name is None and req.vcs:
            # A source control requirement like git+, return as-is
            new_line = req.line
        elif req.name:
            specs = ['{0}{1}'.format(cmp, ver) for cmp, ver in req.specs]
            new_line = req.name + ','.join(specs)
        else:
            raise RuntimeError('Could not process {0}'.format(req.line))

        sanitized.append(new_line + '  # from collection {}'.format(','.join(req.collections)))

    return sanitized


EXCLUDE_SYSTEM_REQUIREMENTS = frozenset((
    # obviously already satisfied or unwanted
    'ansible', 'ansible-test',
))


def parse_bindep_lines(lines):
    text = '\n'.join(lines)
    if not text.endswith('\n'):
        text += '\n'
    depends = Depends(text)
    return depends._rules


def render_bindep_data(entry, collections):
    lines = []
    for entry in entry:
        name = entry[0]

        condition_strings = []
        for condition in entry[1]:
            negate_str = '' if condition[0] else '!'
            condition_strings.append(f'{negate_str}{condition[1]}')
        conditions = ' '.join(condition_strings)

        version_strings = []
        for version_c in entry[2]:
            version_strings.append(''.join(version_c))
        versions = ','.join(version_strings)

        lines.append(f'{name} [{conditions}] {versions}'.strip())
    return '\n'.join(lines)


def sanitize_system_requirements(collection_sys_reqs):
    # de-duplication
    consolidated = []
    seen_entries = set()
    for collection, lines in collection_sys_reqs.items():
        try:
            for entry in parse_bindep_lines(lines):
                if not entry:
                    continue

                if entry in seen_entries:
                    for prior_entry in consolidated:
                        if entry == prior_entry:
                            prior_entry[3].append(collection)
                            break
                    continue

                entry_w_collection = entry + ([collection],)

                consolidated.append(entry_w_collection)
                seen_entries.add(entry)
        except Exception as e:
            raise RuntimeError(
                'Failed to parse system requirement from {}, lines: \n{}\nerror: \n{}'.format(
                    collection, lines, str(e)
                ))

    # removal of unwanted packages
    sanitized = []
    for entry in consolidated:
        name = entry[0]
        if name and name.lower() in EXCLUDE_SYSTEM_REQUIREMENTS:
            continue

        new_line = render_bindep_data(entry)

        sanitized.append(new_line + '  # from collection {}'.format(','.join(entry[3])))

    return sanitized
