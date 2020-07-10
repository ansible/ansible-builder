import os

from . import constants


class AdditionalBuildSteps:
    def __init__(self, additional_steps):
        """Allows for additional prepended / appended build steps to be
        in the Containerfile or Dockerfile.
        """
        self.steps = []
        if isinstance(additional_steps, str):
            lines = additional_steps.strip().splitlines()
        elif isinstance(additional_steps, list):
            lines = additional_steps
        else:
            lines = []
            print("Unknown type found for additional_build_steps.  Ignoring...")

        self.steps.extend(lines)

    def __iter__(self):
        return iter(self.steps)


class IntrospectionSteps:
    def __init__(self, context_file):
        self.steps = []
        self.steps.extend([
            "ADD {} /usr/local/bin/introspect".format(context_file),
            "RUN chmod +x /usr/local/bin/introspect"
        ])

    def __iter__(self):
        return iter(self.steps)


class GalaxySteps:
    def __init__(self, requirements_naming):
        """Assumes given requirements file name has been placed in the build context
        """
        self.steps = []
        self.steps.append(
            "ADD {} /build/".format(requirements_naming)
        )
        self.steps.extend([
            "",
            "RUN ansible-galaxy role install -r /build/{0} --roles-path {1}".format(
                requirements_naming, constants.base_roles_path),
            "RUN ansible-galaxy collection install -r /build/{0} --collections-path {1}".format(
                requirements_naming, constants.base_collections_path)
        ])

    def __iter__(self):
        return iter(self.steps)


class PipSteps:
    def __init__(self, context_file, collection_files):
        """Allows for 1 python requirement file in the build context
        In collection files, expects a list of relative paths where python requirements files live
        returns a list of commands to put in Containerfile
        """
        self.steps = []
        sanitized_files = []
        if context_file:
            # requirements file added to build context
            file_naming = os.path.basename(context_file)
            self.steps.append(
                "ADD {} /build/".format(file_naming)
            )
            sanitized_files.append(os.path.join('/build/', file_naming))

        for entry in collection_files:
            # requirements file from collection, use absolute path
            sanitized_files.append(os.path.join(
                constants.base_collections_path, 'ansible_collections', entry
            ))

        if len(sanitized_files) == 1:
            self.steps.append(
                "RUN pip3 install -r {content}".format(content=sanitized_files[0])
            )
        elif len(sanitized_files) > 1:
            line_return = ' \\\n    -r '
            self.steps.extend([
                "RUN pip3 install{line_return}{content}".format(
                    line_return=line_return,
                    content=line_return.join(sanitized_files)
                )
            ])

    def __iter__(self):
        return iter(self.steps)
