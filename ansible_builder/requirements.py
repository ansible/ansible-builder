import requirements


EXCLUDE_REQUIREMENTS = frozenset((
    # obviously already satisfied or unwanted
    'ansible', 'ansible-base', 'python',
    # general python test requirements
    'tox', 'pycodestyle', 'yamllint', 'pylint',
    'flake8', 'pytest', 'pytest-xdist', 'coverage', 'mock',
    # test requirements highly specific to Ansible testing
    'ansible-lint', 'molecule', 'galaxy-importer', 'voluptuous',
    # already present in image for py3 environments
    'yaml', 'pyyaml', 'json',
))


def sanitize_requirements(collection_py_reqs):
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
            print('Warning: failed to parse requirments from {}, error: {}'.format(collection, e))

    # removal of unwanted packages
    sanitized = []
    for req in consolidated:
        if req.name and req.name.lower() in EXCLUDE_REQUIREMENTS:
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
