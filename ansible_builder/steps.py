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


class GalaxyInstallSteps(Steps):
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
                requirements_naming, constants.base_collections_path),
            "",
            "RUN mkdir -p {0} {1}".format(constants.base_roles_path, constants.base_collections_path),
        ])


class GalaxyCopySteps(Steps):
    def __init__(self):
        """Assumes given requirements file name has been placed in the build context
        """
        self.steps = []
        self.steps.extend([
            "",
            "COPY --from=galaxy {0} {0}".format(constants.base_roles_path),
            "COPY --from=galaxy {0} {0}".format(constants.base_collections_path),
            "",
        ])


class AnsibleConfigSteps(Steps):
    def __init__(self, ansible_config):
        """Copies a user's ansible.cfg file for accessing Galaxy server"""
        self.steps = []
        self.steps.extend([
            "ADD ansible.cfg ~/.ansible.cfg",
            "",
        ])
