import os

from . import constants


def galaxy_steps(requirements_naming):
    """Assumes given requirements file name has been placed in the build context
    """
    steps = []
    steps.append(
        "ADD {} /build/".format(requirements_naming)
    )
    steps.extend([
        "",
        "RUN ansible-galaxy role install -r /build/{0} --roles-path {1}".format(
            requirements_naming, constants.base_roles_path),
        "RUN ansible-galaxy collection install -r /build/{0} --collections-path {1}".format(
            requirements_naming, constants.base_collections_path)
    ])
    return steps


def pip_steps(context_file, collection_files):
    """Allows for 1 python requirement file in the build context
    In collection files, expects a list of relative paths where python requirements files live
    returns a list of commands to put in Containerfile
    """
    steps = []
    sanitized_files = []
    if context_file:
        # requirements file added to build context
        file_naming = os.path.basename(context_file)
        steps.append(
            "ADD {} /build/".format(file_naming)
        )
        sanitized_files.append(file_naming)

    for entry in collection_files:
        # requirements file from collection, use absolute path
        sanitized_files.append(os.path.join(
            constants.base_collections_path, 'ansible_collections', entry
        ))

    if len(sanitized_files) == 1:
        steps.append(
            "RUN pip3 install -r {content}".format(content=sanitized_files[0])
        )
    elif len(sanitized_files) > 1:
        line_return = ' \\\n    -r '
        steps.extend([
            "RUN pip3 install{line_return}{content}".format(
                line_return=line_return,
                content=line_return.join(sanitized_files)
            )
        ])
    return steps
