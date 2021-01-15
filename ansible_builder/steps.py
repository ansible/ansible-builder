import sys
import os

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
            "ADD {0} /build".format(
                constants.user_content_subfolder)
        )
        self.steps.extend([
            "",
            "WORKDIR /build",
            "RUN ansible-galaxy role install -r {0} --roles-path {1}".format(
                requirements_naming, constants.base_roles_path),
            "RUN ansible-galaxy collection install $ANSIBLE_GALAXY_CLI_COLLECTION_OPTS -r {0} --collections-path {1}".format(
                requirements_naming, constants.base_collections_path),
        ])


class GalaxyCopySteps(Steps):
    def __init__(self):
        """Assumes given requirements file name has been placed in the build context
        """
        self.steps = []
        self.steps.extend([
            "",
            "COPY --from=galaxy {0} {0}".format(
                os.path.dirname(constants.base_collections_path.rstrip('/'))  # /usr/share/ansible
            ),
            "",
        ])


class AnsibleConfigSteps(Steps):
    def __init__(self, context_file):
        """Copies a user's ansible.cfg file for accessing Galaxy server"""
        self.steps = []
        self.steps.extend([
            f"ADD {context_file} ~/.ansible.cfg",
            "",
        ])
