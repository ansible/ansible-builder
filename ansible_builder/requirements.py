import logging
import requirements
from pkg_resources import safe_name


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


def sanitize_requirements(collection_py_reqs):
    """
    Cleanup Python requirements by removing duplicates and excluded packages.

    The user requirements file will go through the deduplication process, but
    skips the special package exclusion process.

    :param dict collection_py_reqs: A dict of lists of Python requirements, keyed
        by fully qualified collection name. The special key `user` holds requirements
        from the user specified requirements file from the ``--user-pip`` CLI option.

    :returns: A finalized list of sanitized Python requirements.
    """
    # de-duplication
    consolidated = []
    seen_pkgs = set()

    for collection, lines in collection_py_reqs.items():
        try:
            for req in requirements.parse('\n'.join(lines)):
                if req.specifier:
                    req.name = safe_name(req.name)
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
            logger.warning('Warning: failed to parse requirements from %s, error: %s', collection, e)

    # removal of unwanted packages
    sanitized = []
    for req in consolidated:
        # Exclude packages, unless it was present in the user supplied requirements.
        if req.name and req.name.lower() in EXCLUDE_REQUIREMENTS and 'user' not in req.collections:
            logger.debug('# Excluding requirement %s from %s', req.name, req.collections)
            continue
        if req.vcs or req.uri:
            # Requirement like git+ or http return as-is
            new_line = req.line
        elif req.name:
            specs = ['{0}{1}'.format(cmp, ver) for cmp, ver in req.specs]
            new_line = req.name + ','.join(specs)
        else:
            raise RuntimeError('Could not process {0}'.format(req.line))

        sanitized.append(new_line + '  # from collection {}'.format(','.join(req.collections)))

    return sanitized
