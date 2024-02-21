import logging
import os

from . import constants
from .containerfile import Containerfile
from .policies import PolicyChoices, IgnoreAll, ExactReference
from .user_definition import UserDefinition
from .utils import run_command


logger = logging.getLogger(__name__)


class AnsibleBuilder:
    def __init__(self,
                 action=None,
                 filename=constants.default_file,
                 build_args=None,
                 build_context=constants.default_build_context,
                 tag=None,
                 container_runtime=constants.default_container_runtime,
                 output_filename=None,
                 no_cache=False,
                 prune_images=False,
                 verbosity=constants.default_verbosity,
                 galaxy_keyring=None,
                 galaxy_required_valid_signature_count=None,
                 galaxy_ignore_signature_status_codes=(),
                 container_policy=None,
                 container_keyring=None,
                 squash=None,
                 ):
        """
        :param str galaxy_keyring: GPG keyring file used by ansible-galaxy to opportunistically validate collection signatures.
        :param str galaxy_required_valid_signature_count: Number of sigs (prepend + to disallow no sig( required for ansible-galaxy to accept collections.
        :param str galaxy_ignore_signature_status_codes: GPG Status code to ignore when validating galaxy collections.
        :param str container_policy: The container validation policy. A valid string value from the PolicyChoices enum.
        """

        if not galaxy_keyring and (galaxy_required_valid_signature_count or galaxy_ignore_signature_status_codes):
            raise ValueError("--galaxy-required-valid-signature-count and --galaxy-ignore-signature-status-code may not be set without --galaxy-keyring")

        self.action = action

        # Read and validate the EE file early
        self.definition = UserDefinition(filename=filename)
        self.definition.validate()

        self.tags = tag or []
        self.build_context = build_context
        self.build_outputs_dir = os.path.join(
            build_context, constants.user_content_subfolder)
        self.container_runtime = container_runtime
        self.build_args = build_args or {}
        self.no_cache = no_cache
        self.prune_images = prune_images
        self.containerfile = Containerfile(
            definition=self.definition,
            build_context=self.build_context,
            container_runtime=self.container_runtime,
            output_filename=output_filename,
            galaxy_keyring=galaxy_keyring,
            galaxy_required_valid_signature_count=galaxy_required_valid_signature_count,
            galaxy_ignore_signature_status_codes=galaxy_ignore_signature_status_codes)
        self.verbosity = verbosity
        self.container_policy, self.container_keyring = self._handle_image_validation_opts(container_policy, container_keyring)
        self.squash = squash

    def _handle_image_validation_opts(self, policy, keyring):
        """
        Process the container_policy and container_keyring arguments.

        :param str policy: The container_policy value.
        :param str keyring: The container_keyring value.

        The container_policy and container_keyring arguments come from the CLI
        and work together to help build or use a podman policy.json file used
        to do image validation. Depending on the policy being used, the keyring
        may or may not be necessary.

        The keyring, if required, must be a valid path, and will be transformed
        to an absolute path to be used in the policy.json file.

        :returns: A tuple of a PolicyChoices enum and abs path to the keyring.
        """
        resolved_policy = None
        resolved_keyring = None

        if policy is not None:
            if self.version == 1:
                raise ValueError(f'--container-policy not valid with version {self.version} format')

            # Require podman runtime
            if self.container_runtime != 'podman':
                raise ValueError('--container-policy is only valid with the podman runtime')

            resolved_policy = PolicyChoices(policy)

            # Require keyring if we write a policy file
            if resolved_policy == PolicyChoices.SIG_REQ and keyring is None:
                raise ValueError(f'--container-policy={resolved_policy.value} requires --container-keyring')

            # Do not allow images to be defined with --build-arg CLI option if
            # any sig policy is defined.
            for key, _ in self.build_args.items():
                if key in ('EE_BASE_IMAGE', 'EE_BUILDER_IMAGE'):
                    raise ValueError(f'{key} not allowed in --build-arg option with version 2 format')

        if keyring is not None:
            # Require the correct policy to be specified
            if resolved_policy is None:
                raise ValueError('--container-keyring requires --container-policy')
            elif resolved_policy != PolicyChoices.SIG_REQ:
                raise ValueError(f'--container-keyring is not valid with --container-policy={resolved_policy.value}')

            # Set the keyring to an absolute path to be referenced in the policy file.
            if not os.path.exists(keyring):
                raise ValueError('--container-keyring error: file does not exist')
            if not os.path.isfile(keyring):
                raise ValueError('--container-keyring error: not a file')
            resolved_keyring = os.path.abspath(keyring)

        return (resolved_policy, resolved_keyring)

    @property
    def version(self):
        return self.definition.version

    @property
    def ansible_config(self):
        return self.definition.ansible_config

    def create(self):
        logger.debug('Ansible Builder is generating your execution environment build context.')
        self.containerfile.prepare()
        return self.containerfile.write()

    @property
    def prune_image_command(self):
        command = [
            self.container_runtime, "image",
            "prune", "--force"
        ]
        return command

    @property
    def build_command(self):
        command = [
            self.container_runtime, "build",
            "-f", self.containerfile.path
        ]

        for tag in self.tags:
            command.extend(["-t", tag])

        for key, value in self.build_args.items():
            if value:
                build_arg = f"--build-arg={key}={value}"
            else:
                build_arg = f"--build-arg={key}"

            command.append(build_arg)

        if self.no_cache:
            command.append('--no-cache')

        # Image layer squashing works only with podman. Still experimental for docker.
        if self.container_runtime == 'podman' and self.squash and self.squash != 'off':
            if self.squash == 'new':
                command.append('--squash')
            elif self.squash == 'all':
                command.append('--squash-all')

        if self.container_policy:
            logger.debug('Container policy is %s', PolicyChoices(self.container_policy).value)

            if self.container_policy == PolicyChoices.IGNORE:
                policy = IgnoreAll()
            elif self.container_policy == PolicyChoices.SIG_REQ:
                logger.debug('Container validation keyring: %s', self.container_keyring)
                policy = ExactReference(self.container_keyring)
                if self.definition.base_image:
                    policy.add_image(self.definition.base_image.name,
                                     self.definition.base_image.signature_original_name)
                if self.definition.builder_image:
                    policy.add_image(self.definition.builder_image.name,
                                     self.definition.builder_image.signature_original_name)

            # SYSTEM is just a no-op for writing the policy file, but we still
            # need to use the --pull-always option so that the system policy
            # files work correctly if they require validating signatures.
            if self.container_policy != PolicyChoices.SYSTEM:
                policy_file_path = os.path.join(self.build_context, constants.default_policy_file_name)
                logger.debug('Writing podman policy file %s', policy_file_path)
                policy.write_policy(policy_file_path)
                command.append(f'--signature-policy={policy_file_path}')

            if self.container_policy != PolicyChoices.IGNORE:
                command.append('--pull-always')

        command.append(self.build_context)

        return command

    def build(self):
        self.create()
        logger.debug('Ansible Builder is building your execution environment image. Tags: %s', ", ".join(self.tags))
        run_command(self.build_command)
        if self.prune_images:
            logger.debug('Removing all dangling images')
            run_command(self.prune_image_command)
        return True
