import os
import sys

from . import constants
from .exceptions import DefinitionError


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
            raise DefinitionError(
                """
                Error: Unknown type found for additional_build_steps; must be list or multi-line string.
                """
            )
            sys.exit(1)
        self.steps.extend(lines)

    def __iter__(self):
        return iter(self.steps)


class GalaxySteps(Steps):
    def __init__(self, requirements_naming):
        """Assumes given requirements file name has been placed in the build context
        """
        self.steps = []
        self.steps.append(
            "ADD {0} /build/".format(requirements_naming)
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
        """The context file here must be the output from bindep"""
        self.steps = []
        if not context_file:
            return

        # requirements file added to build context
        self.steps.append("ADD {0} /build/".format(context_file))
        container_path = os.path.join('/build/', context_file)
        self.steps.append(
            "RUN dnf -y install $(cat {0})".format(container_path)
        )


class PipSteps(Steps):
    def __init__(self, context_file):
        """Allows for 1 python requirement file in the build context"""
        self.steps = []
        if not context_file:
            return

        # requirements file added to build context
        self.steps.append("ADD {0} /build/".format(context_file))
        container_path = os.path.join('/build/', context_file)
        self.steps.append(
            "RUN pip3 install --upgrade -r {content}".format(content=container_path)
        )
