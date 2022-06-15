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


class BuildContextSteps(Steps):
    def __init__(self):
        self.steps = [
            "ADD {0} /build".format(constants.user_content_subfolder),
            "WORKDIR /build",
            "",
        ]


class GalaxyInstallSteps(Steps):
    def __init__(self, requirements_naming, galaxy_keyring, galaxy_ignore_signature_status_codes, galaxy_required_valid_signature_count):
        """Assumes given requirements file name and keyring has been placed in the build context.

        :param str galaxy_keyring: GPG keyring file used by ansible-galaxy to opportunistically validate collection signatures.
        :param str galaxy_required_valid_signature_count: Number of sigs (prepend + to disallow no sig) required for ansible-galaxy to accept collections.
        :param str galaxy_ignore_signature_status_codes: GPG Status codes to ignore when validating galaxy collections.
        """

        env = ""
        install_opts = f"-r {requirements_naming} --collections-path \"{constants.base_collections_path}\""

        if galaxy_ignore_signature_status_codes:
            for code in galaxy_ignore_signature_status_codes:
                install_opts += f" --ignore-signature-status-code {code}"

        if galaxy_required_valid_signature_count:
            install_opts += f" --required-valid-signature-count {galaxy_required_valid_signature_count}"

        if galaxy_keyring:
            install_opts += f" --keyring \"{galaxy_keyring}\""
        else:
            # We have to use the environment variable to disable signature
            # verification because older versions (<2.13) of ansible-galaxy do
            # not support the --disable-gpg-verify option. We don't use ENV in
            # the Containerfile since we need it only during the build and not
            # in the final image.
            env = "ANSIBLE_GALAXY_DISABLE_GPG_VERIFY=1 "

        self.steps = [
            f"RUN ansible-galaxy role install $ANSIBLE_GALAXY_CLI_ROLE_OPTS -r {requirements_naming} --roles-path \"{constants.base_roles_path}\"",
            f"RUN {env}ansible-galaxy collection install $ANSIBLE_GALAXY_CLI_COLLECTION_OPTS {install_opts}",
        ]


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
