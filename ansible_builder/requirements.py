import logging

from .exceptions import DefinitionError

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
            logger.warn(
                'Failed to parse system requirement from {}, lines: \n{}\nerror: \n{}'.format(
                    collection, lines, str(e)
                )
            )

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
    'python', 'ansible', 'ansible-test',
))


def parse_bindep_lines(lines):
    text = '\n'.join(lines)
    if not text.endswith('\n'):
        text += '\n'
    depends = Depends(text)
    return depends._rules


def render_bindep_data(entry):
    lines = []
    for entry in entry:
        name = entry[0]
        this_line = name

        condition_strings = []
        for condition in entry[1]:
            negate_str = '' if condition[0] else '!'
            condition_strings.append(f'{negate_str}{condition[1]}')
        conditions = ' '.join(condition_strings)
        if conditions:
            this_line += f' [{conditions}]'

        version_strings = []
        for version_c in entry[2]:
            version_strings.append(''.join(version_c))
        versions = ','.join(version_strings)
        if versions:
            this_line += f' {versions}'

        lines.append(this_line)

    return '\n'.join(lines)


def sanitize_system_requirements(collection_sys_reqs):
    # de-duplication
    consolidated = []
    seen_entries = set()
    for collection, lines in collection_sys_reqs.items():
        try:
            parsed_data = parse_bindep_lines(lines)
        except Exception:
            # The parent exception is printed to terminal due to how exception handling works
            raise DefinitionError(
                'Failed to parse system requirement from `{}`\nbindep lines that caused error: \n{}'.format(
                    collection, '\n'.join(lines)
                )
            )
        for entry in parsed_data:
            if not entry:
                continue

            if repr(entry[:3]) in seen_entries:  # TODO maybe find a better way of this...
                for prior_entry in consolidated:
                    if repr(entry[:3]) == repr(prior_entry[:3]):
                        prior_entry[3].append(collection)
                        break
                else:
                    print(repr(entry))
                    print(seen_entries)
                    raise Exception
                continue

            entry_w_collection = entry + ([collection],)

            consolidated.append(entry_w_collection)
            seen_entries.add(repr(entry[:3]))

    # removal of unwanted packages
    sanitized = []
    for entry in consolidated:
        name = entry[0]
        if name and name.lower() in EXCLUDE_SYSTEM_REQUIREMENTS:
            continue

        new_line = render_bindep_data([entry])

        sanitized.append(new_line + '  # from collection {}'.format(','.join(entry[3])))

    return sanitized
