import logging
import os

from . import constants
from .policies import PolicyChoices, IgnoreAll, ExactReference
from .steps import (
    AdditionalBuildSteps, BuildContextSteps, GalaxyInstallSteps, GalaxyCopySteps, AnsibleConfigSteps
)
from .user_definition import UserDefinition
from .utils import run_command, copy_file


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
            if self.version != "2":
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
        return self.write_containerfile()

    def write_containerfile(self):
        # File preparation
        self.containerfile.create_folder_copy_files()

        # First stage, galaxy
        self.containerfile.prepare_galaxy_stage_steps()
        self.containerfile.prepare_ansible_config_file()
        self.containerfile.prepare_build_context()
        self.containerfile.prepare_galaxy_install_steps()

        # Second stage, builder
        self.containerfile.prepare_build_stage_steps()
        self.containerfile.prepare_galaxy_copy_steps()
        self.containerfile.prepare_introspect_assemble_steps()

        # Second stage
        self.containerfile.prepare_final_stage_steps()
        self.containerfile.prepare_prepended_steps()
        self.containerfile.prepare_galaxy_copy_steps()
        self.containerfile.prepare_system_runtime_deps_steps()
        self.containerfile.prepare_appended_steps()
        self.containerfile.prepare_label_steps()
        logger.debug('Rewriting Containerfile to capture collection requirements')
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
        logger.debug('Ansible Builder is building your execution environment image. Tags: %s', ", ".join(self.tags))
        self.write_containerfile()
        run_command(self.build_command)
        if self.prune_images:
            logger.debug('Removing all dangling images')
            run_command(self.prune_image_command)
        return True


class Containerfile:
    newline_char = '\n'

    def __init__(self, definition,
                 build_context=None,
                 container_runtime=None,
                 output_filename=None,
                 galaxy_keyring=None,
                 galaxy_required_valid_signature_count=None,
                 galaxy_ignore_signature_status_codes=()):
        """
        :param str galaxy_keyring: GPG keyring file used by ansible-galaxy to opportunistically validate collection signatures.
        :param str galaxy_required_valid_signature_count: Number of sigs (prepend + to disallow no sig) required for ansible-galaxy to accept collections.
        :param str galaxy_ignore_signature_status_codes: GPG Status codes to ignore when validating galaxy collections.
        """

        self.build_context = build_context
        self.build_outputs_dir = os.path.join(
            build_context, constants.user_content_subfolder)
        self.definition = definition
        if output_filename is None:
            filename = constants.runtime_files[container_runtime]
        else:
            filename = output_filename
        self.path = os.path.join(self.build_context, filename)
        self.container_runtime = container_runtime
        self.original_galaxy_keyring = galaxy_keyring
        self.copied_galaxy_keyring = None
        self.galaxy_required_valid_signature_count = galaxy_required_valid_signature_count
        self.galaxy_ignore_signature_status_codes = galaxy_ignore_signature_status_codes

        # Build args all need to go at top of file to avoid errors
        self.steps = [
            "ARG EE_BASE_IMAGE={}".format(
                self.definition.build_arg_defaults['EE_BASE_IMAGE']
            ),
            "ARG EE_BUILDER_IMAGE={}".format(
                self.definition.build_arg_defaults['EE_BUILDER_IMAGE']
            ),
        ]

    def create_folder_copy_files(self):
        """Creates the build context file for this Containerfile
        moves files from the definition into the folder
        """
        os.makedirs(self.build_outputs_dir, exist_ok=True)

        for item, new_name in constants.CONTEXT_FILES.items():
            requirement_path = self.definition.get_dep_abs_path(item)
            if requirement_path is None:
                continue
            dest = os.path.join(
                self.build_context, constants.user_content_subfolder, new_name)
            copy_file(requirement_path, dest)

        if self.original_galaxy_keyring:
            self.copied_galaxy_keyring = constants.default_keyring_name
            copy_file(self.original_galaxy_keyring, os.path.join(self.build_outputs_dir, self.copied_galaxy_keyring))

        if self.definition.ansible_config:
            copy_file(
                self.definition.ansible_config,
                os.path.join(self.build_outputs_dir, 'ansible.cfg')
            )

    def prepare_ansible_config_file(self):
        ansible_config_file_path = self.definition.ansible_config
        if ansible_config_file_path:
            context_file_path = os.path.join(
                constants.user_content_subfolder, 'ansible.cfg')
            return self.steps.extend(AnsibleConfigSteps(context_file_path))

    def prepare_prepended_steps(self):
        additional_prepend_steps = self.definition.get_additional_commands()
        if additional_prepend_steps:
            prepended_steps = additional_prepend_steps.get('prepend')
            if prepended_steps:
                return self.steps.extend(AdditionalBuildSteps(prepended_steps))

        return False

    def prepare_appended_steps(self):
        additional_append_steps = self.definition.get_additional_commands()
        if additional_append_steps:
            appended_steps = additional_append_steps.get('append')
            if appended_steps:
                return self.steps.extend(AdditionalBuildSteps(appended_steps))

        return False

    def prepare_label_steps(self):
        self.steps.extend([
            "LABEL ansible-execution-environment=true",
        ])

        return self.steps

    def prepare_build_context(self):
        if any(self.definition.get_dep_abs_path(thing) for thing in ('galaxy', 'system', 'python')):
            self.steps.extend(BuildContextSteps())
        return self.steps

    def prepare_galaxy_install_steps(self):
        if self.definition.get_dep_abs_path('galaxy'):
            self.steps.extend(GalaxyInstallSteps(constants.CONTEXT_FILES['galaxy'],
                                                 self.copied_galaxy_keyring,
                                                 self.galaxy_ignore_signature_status_codes,
                                                 self.galaxy_required_valid_signature_count))
        return self.steps

    def prepare_introspect_assemble_steps(self):
        # The introspect/assemble block is valid if there are any form of requirements
        if any(self.definition.get_dep_abs_path(thing) for thing in ('galaxy', 'system', 'python')):

            introspect_cmd = "RUN ansible-builder introspect --sanitize"

            requirements_file_exists = os.path.exists(os.path.join(
                self.build_outputs_dir, constants.CONTEXT_FILES['python']
            ))
            if requirements_file_exists:
                relative_requirements_path = os.path.join(constants.user_content_subfolder, constants.CONTEXT_FILES['python'])
                self.steps.append(f"ADD {relative_requirements_path} {constants.CONTEXT_FILES['python']}")
                # WORKDIR is /build, so we use the (shorter) relative paths there
                introspect_cmd += " --user-pip={0}".format(constants.CONTEXT_FILES['python'])
            bindep_exists = os.path.exists(os.path.join(self.build_outputs_dir, constants.CONTEXT_FILES['system']))
            if bindep_exists:
                relative_bindep_path = os.path.join(constants.user_content_subfolder, constants.CONTEXT_FILES['system'])
                self.steps.append(f"ADD {relative_bindep_path} {constants.CONTEXT_FILES['system']}")
                introspect_cmd += " --user-bindep={0}".format(constants.CONTEXT_FILES['system'])

            introspect_cmd += " --write-bindep=/tmp/src/bindep.txt --write-pip=/tmp/src/requirements.txt"

            self.steps.append(introspect_cmd)
            self.steps.append("RUN assemble")

        return self.steps

    def prepare_system_runtime_deps_steps(self):
        self.steps.extend([
            "COPY --from=builder /output/ /output/",
            "RUN /output/install-from-bindep && rm -rf /output/wheels",
        ])

        return self.steps

    def prepare_galaxy_stage_steps(self):
        self.steps.extend([
            "",
            "FROM $EE_BASE_IMAGE as galaxy",
            "ARG ANSIBLE_GALAXY_CLI_COLLECTION_OPTS={}".format(
                self.definition.build_arg_defaults['ANSIBLE_GALAXY_CLI_COLLECTION_OPTS']
            ),
            "ARG ANSIBLE_GALAXY_CLI_ROLE_OPTS={}".format(
                self.definition.build_arg_defaults['ANSIBLE_GALAXY_CLI_ROLE_OPTS']
            ),
            "USER root",
            ""
        ])

        return self.steps

    def prepare_build_stage_steps(self):
        self.steps.extend([
            "",
            "FROM $EE_BUILDER_IMAGE as builder"
            "",
        ])

        return self.steps

    def prepare_final_stage_steps(self):
        self.steps.extend([
            "",
            "FROM $EE_BASE_IMAGE",
            "USER root"
            "",
        ])
        return self.steps

    def prepare_galaxy_copy_steps(self):
        if self.definition.get_dep_abs_path('galaxy'):
            self.steps.extend(GalaxyCopySteps())
        return self.steps

    def write(self):
        with open(self.path, 'w') as f:
            for step in self.steps:
                f.write(step + self.newline_char)

        return True
