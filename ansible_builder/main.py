import logging
import os

from . import constants
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
                 galaxy_ignore_signature_status_codes=()):
        """
        :param str galaxy_keyring: GPG keyring file used by ansible-galaxy to opportunistically validate collection signatures.
        :param str galaxy_required_valid_signature_count: Number of sigs (prepend + to disallow no sig( required for ansible-galaxy to accept collections.
        :param str galaxy_ignore_signature_status_codes: GPG Status code to ignore when validating galaxy collections.
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

        command.append(self.build_context)

        if self.no_cache:
            command.append('--no-cache')

        return command

    def build(self):
        logger.debug(f'Ansible Builder is building your execution environment image. Tags: {", ".join(self.tags)}')
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
                 keyring=None,
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
