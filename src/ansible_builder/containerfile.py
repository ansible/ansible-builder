import importlib.resources
import logging
import os

from pathlib import Path

from . import constants
from .user_definition import UserDefinition
from .utils import copy_directory, copy_file


logger = logging.getLogger(__name__)


class Containerfile:
    newline_char = '\n'

    def __init__(self, definition: UserDefinition,
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
        self.steps: list = []

    def prepare(self):
        """
        Prepares the steps for the run-time specific build file.

        Incrementally builds the `self.steps` attribute by extending it with the
        info to eventually be written directly to the container definition file
        via a separate call to the `Containerfile.write()` method.
        """

        # Build args all need to go at top of file to avoid errors
        self._insert_global_args(include_values=True)

        ######################################################################
        # Zero stage: prep base image
        ######################################################################

        # 'base' (possibly customized) will be used by future build stages
        self.steps.extend([
            "# Base build stage",
            "FROM $EE_BASE_IMAGE as base",
            "USER root",
        ])

        self._insert_global_args()
        self._insert_custom_steps('prepend_base')

        if not self.definition.builder_image:
            if self.definition.python_package_system:
                self.steps.append('RUN $PKGMGR install $PYPKG -y ; if [ -z $PKGMGR_PRESERVE_CACHE ]; then $PKGMGR clean all; fi')

            # We should always make sure pip is available for later stages.
            self.steps.append('RUN $PYCMD -m ensurepip')

            if self.definition.ansible_ref_install_list:
                self.steps.append('RUN $PYCMD -m pip install --no-cache-dir $ANSIBLE_INSTALL_REFS')

        self._create_folder_copy_files()
        self._insert_custom_steps('append_base')

        ######################################################################
        # First stage (aka, galaxy): install roles/collections
        #
        # NOTE: This stage is skipped if there are no galaxy requirements.
        ######################################################################

        if self.definition.get_dep_abs_path('galaxy'):
            self.steps.extend([
                "",
                "# Galaxy build stage",
                "FROM base as galaxy",
            ])

            self._insert_global_args()
            self._insert_custom_steps('prepend_galaxy')

            # Run the check for the 'ansible-galaxy' executable. This will fail
            # the build if the command is not found.
            self.steps.append("RUN /output/scripts/check_galaxy")

            self._prepare_ansible_config_file()
            self._prepare_build_context()
            self._prepare_galaxy_install_steps()
            self._insert_custom_steps('append_galaxy')

        ######################################################################
        # Second stage (aka, builder): assemble (pip installs, bindep run)
        ######################################################################

        if self.definition.builder_image:
            # Note: A builder image can be specified only in V1 or V2 schema.
            image = "$EE_BUILDER_IMAGE"
        else:
            # dynamic builder, create from customized base
            image = "base"

        self.steps.extend([
            "",
            "# Builder build stage",
            f"FROM {image} as builder",
            "WORKDIR /build",
        ])

        self._insert_global_args()

        if image == "base":
            self.steps.append("RUN $PYCMD -m pip install --no-cache-dir bindep pyyaml requirements-parser")

        self._insert_custom_steps('prepend_builder')
        self._prepare_galaxy_copy_steps()
        self._prepare_introspect_assemble_steps()
        self._insert_custom_steps('append_builder')

        ######################################################################
        # Final stage: package manager installs from bindep output
        ######################################################################

        self.steps.extend([
            "",
            "# Final build stage",
            "FROM base as final",
        ])

        self._insert_global_args()
        self._insert_custom_steps('prepend_final')

        # Run the check for 'ansible' and 'ansible-runner' installations for
        # any EE version 3 or above, unless explicitly skipped.
        if self.definition.version >= 3 and not self.definition.options['skip_ansible_check']:
            self.steps.append("RUN /output/scripts/check_ansible $PYCMD")

        self._prepare_galaxy_copy_steps()
        self._prepare_system_runtime_deps_steps()

        if self.definition.version >= 3 and self.definition.options['relax_passwd_permissions']:
            self._relax_etc_passwd_permissions()

        if self.definition.version >= 3 and (final_workdir := self.definition.options['workdir']):
            self._prepare_final_workdir(final_workdir)

        # install init package if specified
        # FUTURE: could move this into the pre-install wheel phase
        if init_pip_pkg := self.definition.container_init.get('package_pip'):
            self.steps.append(f"RUN $PYCMD -m pip install --no-cache-dir '{init_pip_pkg}'")

        self._insert_custom_steps('append_final')

        # Purge the temporary /output directory used in intermediate stages
        self.steps.append("RUN rm -rf /output")

        self._prepare_label_steps()
        if self.definition.version >= 3 and (uid := self.definition.options['user']):
            self._prepare_user_steps(uid)
        self._prepare_entrypoint_steps()

    def write(self):
        """
        Writes the steps (built via the `Containerfile.prepare()` method) for
        the runtime-specific build file (Dockerfile or Containerfile) to the
        context directory.
        """
        with open(self.path, 'w') as f:
            for step in self.steps:
                f.write(step + self.newline_char)
        return True

    def _insert_global_args(self, include_values: bool = False):
        """
        Insert Containerfile ARGs and, possibly, their values.

        An ARG with a None or empty value will not be included.
        """

        # ARGs will be output in the order listed below. Keys with value `None` will be omitted, but empty string values
        # will still appear in the output (this allows them to be set at runtime).
        global_args = {
            'EE_BASE_IMAGE': self.definition.build_arg_defaults['EE_BASE_IMAGE'],
            # this is only applicable for < v3 definitions and will be removed elsewhere for newer schema
            'EE_BUILDER_IMAGE': self.definition.build_arg_defaults['EE_BUILDER_IMAGE'],
            'PYCMD': self.definition.python_path or '/usr/bin/python3',
            'PYPKG': self.definition.python_package_system,
            'PKGMGR_PRESERVE_CACHE': self.definition.build_arg_defaults['PKGMGR_PRESERVE_CACHE'],
            'ANSIBLE_GALAXY_CLI_COLLECTION_OPTS': self.definition.build_arg_defaults['ANSIBLE_GALAXY_CLI_COLLECTION_OPTS'],
            'ANSIBLE_GALAXY_CLI_ROLE_OPTS': self.definition.build_arg_defaults['ANSIBLE_GALAXY_CLI_ROLE_OPTS'],
            'ANSIBLE_INSTALL_REFS': self.definition.ansible_ref_install_list,
        }

        if self.definition.version >= 3:
            global_args['PKGMGR'] = self.definition.options['package_manager_path']

        for arg, value in global_args.items():
            if value is None:
                continue  # an optional or N/A `ARG` we don't even want to emit
            if include_values:  # emit `ARG` directives for empty strings so they can be overridden at build-time
                # quote the value in case it includes spaces
                self.steps.append(f'ARG {arg}="{value}"')
            else:
                self.steps.append(f"ARG {arg}")
        self.steps.append("")

    def _create_folder_copy_files(self):
        """
        Creates the build context directory, and copies any potential context
        files (python, galaxy, or bindep requirements) into it.
        """
        scripts_dir = str(Path(self.build_outputs_dir) / 'scripts')
        os.makedirs(scripts_dir, exist_ok=True)

        for item, new_name in constants.CONTEXT_FILES.items():
            # HACK: new dynamic base/builder
            if not new_name:
                continue

            requirement_path = self.definition.get_dep_abs_path(item)
            if requirement_path is None:
                continue
            dest = os.path.join(
                self.build_context, constants.user_content_subfolder, new_name)

            # Ignore modification time of the requirement file because we could
            # be writing it out dynamically (inline EE reqs), and we only care
            # about the contents anyway.
            copy_file(requirement_path, dest, ignore_mtime=True)

        if self.original_galaxy_keyring:
            copy_file(self.original_galaxy_keyring, os.path.join(self.build_outputs_dir, constants.default_keyring_name))

        self._handle_additional_build_files()

        if self.definition.ansible_config:
            copy_file(
                self.definition.ansible_config,
                os.path.join(self.build_outputs_dir, 'ansible.cfg')
            )

        # HACK: this sucks
        scriptres = importlib.resources.files('ansible_builder._target_scripts')
        for script in ('assemble', 'install-from-bindep', 'introspect.py', 'check_galaxy', 'check_ansible', 'entrypoint'):
            with importlib.resources.as_file(scriptres / script) as script_path:
                copy_file(str(script_path), os.path.join(scripts_dir, script))

        # Later intermediate stages depend on base image containing these scripts.
        # Copy them to a location that we do not need in the final image.
        context_dir = Path(self.build_outputs_dir).stem
        self.steps.append(f'COPY {context_dir}/scripts/ /output/scripts/')

        # The final image will have /output purged, but certain scripts we want
        # to retain in that image.
        self.steps.append(f'COPY {context_dir}/scripts/entrypoint {constants.FINAL_IMAGE_BIN_PATH}/entrypoint')

    def _handle_additional_build_files(self):
        """
        Deal with any files the user wants added to the image build context.

        The 'src' value is either an absolute path, or a path relative to the
        EE definition file. For example, 'src' can be a relative path like
        "data_files/configs/*.cfg", but cannot be "/home/user/files/*.cfg",
        the latter not being relative to the EE.
        """
        for entry in self.definition.additional_build_files:
            src = Path(entry['src'])
            dst = entry['dest']

            # 'src' is either an absolute path or a path glob relative to the EE file
            ee_file = Path(self.definition.filename)
            if src.is_absolute():
                if not src.exists():
                    logger.warning(f"User build file {src} does not exist.")
                    continue
                src_files = [src]
            elif not (src_files := list(ee_file.parent.glob(str(src)))):
                logger.warning(f"No matches for '{src}' in additional_build_files.")
                continue

            final_dst = Path(self.build_outputs_dir) / dst
            logger.debug(f"Creating {final_dst}")
            final_dst.mkdir(parents=True, exist_ok=True)

            for src_file in src_files:
                if src_file.is_dir():
                    copy_directory(src_file, final_dst)
                else:
                    # Destination is the subdir under context plus the basename of the source
                    copy_location = final_dst / src_file.name
                    copy_file(str(src_file), str(copy_location))

    def _prepare_ansible_config_file(self):
        if self.definition.version != 1:
            return

        ansible_config_file_path = self.definition.ansible_config
        if ansible_config_file_path:
            context_file_path = os.path.join(
                constants.user_content_subfolder, 'ansible.cfg')
            self.steps.extend([
                f"COPY {context_file_path} ~/.ansible.cfg",
                "",
            ])

    def _insert_custom_steps(self, section: str):
        additional_steps = self.definition.additional_build_steps
        if additional_steps:
            section_steps = additional_steps.get(section)
            if section_steps:
                if isinstance(section_steps, str):
                    lines = section_steps.strip().splitlines()
                else:
                    lines = section_steps
                self.steps.extend(lines)

    def _relax_etc_passwd_permissions(self):
        self.steps.append(
            "RUN chmod ug+rw /etc/passwd"
        )

    def _prepare_final_workdir(self, workdir: str):
        workdir = workdir.strip()
        if not workdir:
            return

        self.steps.extend([
            f"RUN mkdir -p {workdir} && chgrp 0 {workdir} && chmod -R ug+rwx {workdir}",
            f"WORKDIR {workdir}"
        ])

    def _prepare_label_steps(self):
        self.steps.extend([
            "LABEL ansible-execution-environment=true",
        ])

    def _prepare_build_context(self):
        if any(self.definition.get_dep_abs_path(thing) for thing in ('galaxy', 'system', 'python')):
            self.steps.extend([
                f"COPY {constants.user_content_subfolder} /build",
                "WORKDIR /build",
                "",
            ])

    def _prepare_galaxy_install_steps(self):
        env = ""
        install_opts = f"-r {constants.CONTEXT_FILES['galaxy']} --collections-path \"{constants.base_collections_path}\""

        if self.galaxy_ignore_signature_status_codes:
            for code in self.galaxy_ignore_signature_status_codes:
                install_opts += f" --ignore-signature-status-code {code}"

        if self.galaxy_required_valid_signature_count:
            install_opts += f" --required-valid-signature-count {self.galaxy_required_valid_signature_count}"

        if self.original_galaxy_keyring:
            install_opts += f" --keyring \"{constants.default_keyring_name}\""
        else:
            # We have to use the environment variable to disable signature
            # verification because older versions (<2.13) of ansible-galaxy do
            # not support the --disable-gpg-verify option. We don't use ENV in
            # the Containerfile since we need it only during the build and not
            # in the final image.
            env = "ANSIBLE_GALAXY_DISABLE_GPG_VERIFY=1 "

        self.steps.append(
            f"RUN ansible-galaxy role install $ANSIBLE_GALAXY_CLI_ROLE_OPTS -r {constants.CONTEXT_FILES['galaxy']}"
            f" --roles-path \"{constants.base_roles_path}\"",
        )
        self.steps.append(f"RUN {env}ansible-galaxy collection install $ANSIBLE_GALAXY_CLI_COLLECTION_OPTS {install_opts}")

    def _prepare_introspect_assemble_steps(self):
        # The introspect/assemble block is valid if there are any form of requirements
        if any(self.definition.get_dep_abs_path(thing) for thing in ('galaxy', 'system', 'python')):

            introspect_cmd = "RUN $PYCMD /output/scripts/introspect.py introspect --sanitize"

            requirements_file_exists = os.path.exists(os.path.join(
                self.build_outputs_dir, constants.CONTEXT_FILES['python']
            ))

            if requirements_file_exists:
                relative_requirements_path = os.path.join(constants.user_content_subfolder, constants.CONTEXT_FILES['python'])
                self.steps.append(f"COPY {relative_requirements_path} {constants.CONTEXT_FILES['python']}")
                # WORKDIR is /build, so we use the (shorter) relative paths there
                introspect_cmd += " --user-pip={0}".format(constants.CONTEXT_FILES['python'])
            bindep_exists = os.path.exists(os.path.join(self.build_outputs_dir, constants.CONTEXT_FILES['system']))
            if bindep_exists:
                relative_bindep_path = os.path.join(constants.user_content_subfolder, constants.CONTEXT_FILES['system'])
                self.steps.append(f"COPY {relative_bindep_path} {constants.CONTEXT_FILES['system']}")
                introspect_cmd += " --user-bindep={0}".format(constants.CONTEXT_FILES['system'])

            introspect_cmd += " --write-bindep=/tmp/src/bindep.txt --write-pip=/tmp/src/requirements.txt"

            self.steps.append(introspect_cmd)
            self.steps.append("RUN /output/scripts/assemble")

    def _prepare_system_runtime_deps_steps(self):
        self.steps.extend([
            "COPY --from=builder /output/ /output/",
            "RUN /output/scripts/install-from-bindep && rm -rf /output/wheels",
        ])

    def _prepare_galaxy_copy_steps(self):
        if self.definition.get_dep_abs_path('galaxy'):
            self.steps.extend([
                "",
                "COPY --from=galaxy {0} {0}".format(
                    os.path.dirname(constants.base_collections_path.rstrip('/'))  # /usr/share/ansible
                ),
                "",
            ])

    def _prepare_entrypoint_steps(self):
        if ep := self.definition.container_init.get('entrypoint'):
            self.steps.append(f"ENTRYPOINT {ep}")
        if cmd := self.definition.container_init.get('cmd'):
            self.steps.append(f"CMD {cmd}")

    def _prepare_user_steps(self, uid):
        self.steps.append(f"USER {uid}")
