import os
import sys

from . import constants
from .colors import MessageColors


class Steps:
    def __iter__(self):
        return iter(self.steps)


class AdditionalBuildSteps(Steps):
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
            print(MessageColors.FAIL + "Error: Unknown type found for additional_build_steps; "
                  "must be list or multi-line string." + MessageColors.ENDC)
            sys.exit(1)
        self.steps.extend(lines)

    def __iter__(self):
        return iter(self.steps)


class IntrospectionSteps(Steps):
    def __init__(self, context_file):
        self.steps = []
        self.steps.extend([
            "ADD {} /usr/local/bin/introspect".format(context_file),
            "RUN chmod +x /usr/local/bin/introspect"
        ])


class GalaxySteps(Steps):
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


class BindepSteps(Steps):
    def __init__(self, context_file):
        self.steps = []
        sanitized_files = []
        if context_file:
            # requirements file added to build context
            file_naming = os.path.basename(context_file)
            self.steps.append(
                "ADD {} /build/".format(file_naming)
            )
            sanitized_files.append(os.path.join('/build/', file_naming))

        if sanitized_files:
            self.steps.append(
                "RUN pip3 install bindep"
            )

        for file in sanitized_files:
            self.steps.append(
                "RUN dnf -y install $(bindep -q -f {})".format(file)
            )


class PipSteps(Steps):
    def __init__(self, context_file):
        """Allows for 1 python requirement file in the build context"""
        self.steps = []
        if not context_file:
            return

        # requirements file added to build context
        self.steps.append("ADD {} /build/".format(context_file))
        container_path = os.path.join('/build/', context_file)
        self.steps.append(
            "RUN pip3 install --upgrade -r {content}".format(content=container_path)
        )
