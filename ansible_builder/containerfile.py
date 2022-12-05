import importlib.resources
import os
import pathlib

from . import constants
from .user_definition import UserDefinition
from .utils import copy_file


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
        self.steps.extend([
            "ARG EE_BASE_IMAGE={}".format(
                self.definition.build_arg_defaults['EE_BASE_IMAGE']
            ),
        ])

        if self.definition.builder_image:
            self.steps.append(f"ARG EE_BUILDER_IMAGE={self.definition.build_arg_defaults['EE_BUILDER_IMAGE']}")

        self.steps.append(f"ARG PYCMD={self.definition.python_path or '/usr/bin/python3'}")

        if ansible_refs := self.definition.ansible_ref_install_list:
            self.steps.append(f"ARG ANSIBLE_INSTALL_REFS='{ansible_refs}'")

        self.prepare_dynamic_base_and_builder()
        # File preparation
        self.create_folder_copy_files()

        # First stage, galaxy
        self.prepare_galaxy_stage_steps()
        self.prepare_ansible_config_file()
        self.prepare_build_context()
        self.prepare_galaxy_install_steps()

        # Second stage, builder
        self.prepare_build_stage_steps()
        self.prepare_galaxy_copy_steps()
        self.prepare_introspect_assemble_steps()

        self.prepare_final_stage_steps()
        self.prepare_prepended_steps()
        self.prepare_galaxy_copy_steps()
        self.prepare_system_runtime_deps_steps()
        self.prepare_appended_steps()
        self.prepare_label_steps()

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

    def create_folder_copy_files(self):
        """
        Creates the build context directory, and copies any potential context
        files (python, galaxy, or bindep requirements) into it.
        """
        scripts_dir = str(pathlib.Path(self.build_outputs_dir) / 'scripts')
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
            copy_file(requirement_path, dest)

        if self.original_galaxy_keyring:
            copy_file(self.original_galaxy_keyring, os.path.join(self.build_outputs_dir, constants.default_keyring_name))

        if self.definition.ansible_config:
            copy_file(
                self.definition.ansible_config,
                os.path.join(self.build_outputs_dir, 'ansible.cfg')
            )

        # HACK: this sucks
        scriptres = importlib.resources.files('ansible_builder._target_scripts')
        for script in ('assemble', 'get-extras-packages', 'install-from-bindep', 'introspect.py'):
            with importlib.resources.as_file(scriptres / script) as script_path:
                # FIXME: just use builtin copy?
                copy_file(str(script_path), scripts_dir)

        # later steps depend on base image containing these scripts
        context_dir = pathlib.Path(self.build_outputs_dir).stem
        self.steps.append(f'COPY {context_dir}/scripts/ /output/scripts/')

    def prepare_ansible_config_file(self):
        ansible_config_file_path = self.definition.ansible_config
        if ansible_config_file_path:
            context_file_path = os.path.join(
                constants.user_content_subfolder, 'ansible.cfg')
            self.steps.extend([
                f"ADD {context_file_path} ~/.ansible.cfg",
                "",
            ])

    def prepare_prepended_steps(self):
        additional_prepend_steps = self.definition.get_additional_commands()
        if additional_prepend_steps:
            prepended_steps = additional_prepend_steps.get('prepend')
            if prepended_steps:
                if isinstance(prepended_steps, str):
                    lines = prepended_steps.strip().splitlines()
                else:
                    lines = prepended_steps
                self.steps.extend(lines)

    def prepare_appended_steps(self):
        additional_append_steps = self.definition.get_additional_commands()
        if additional_append_steps:
            appended_steps = additional_append_steps.get('append')
            if appended_steps:
                if isinstance(appended_steps, str):
                    lines = appended_steps.strip().splitlines()
                else:
                    lines = appended_steps
                self.steps.extend(lines)

    def prepare_label_steps(self):
        self.steps.extend([
            "LABEL ansible-execution-environment=true",
        ])

    def prepare_dynamic_base_and_builder(self):
        # 'base' (possibly customized) will be used by future build stages
        self.steps.append("FROM $EE_BASE_IMAGE as base")

        if not self.definition.builder_image:
            if python := self.definition.python_package_name:
                self.steps.append(f'ARG PYPKG={python}')
                # FIXME: better dnf cleanup needed?
                self.steps.append('RUN dnf install $PYPKG -y && dnf clean all')

            if self.definition.ansible_ref_install_list:
                self.steps.append('ARG ANSIBLE_INSTALL_REFS')
                self.steps.append('ARG PYCMD')
                self.steps.append('RUN $PYCMD -m ensurepip && $PYCMD -m pip install --no-cache-dir $ANSIBLE_INSTALL_REFS')

    def prepare_build_context(self):
        if any(self.definition.get_dep_abs_path(thing) for thing in ('galaxy', 'system', 'python')):
            self.steps.extend([
                "ADD {0} /build".format(constants.user_content_subfolder),
                "WORKDIR /build",
                "",
            ])

    def prepare_galaxy_install_steps(self):
        if self.definition.get_dep_abs_path('galaxy'):
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

    def prepare_introspect_assemble_steps(self):
        # The introspect/assemble block is valid if there are any form of requirements
        if any(self.definition.get_dep_abs_path(thing) for thing in ('galaxy', 'system', 'python')):

            introspect_cmd = "RUN $PYCMD /output/scripts/introspect.py introspect --sanitize"

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
            self.steps.append("RUN /output/scripts/assemble")

    def prepare_system_runtime_deps_steps(self):
        self.steps.extend([
            "COPY --from=builder /output/ /output/",
            "RUN /output/scripts/install-from-bindep && rm -rf /output/wheels",
        ])

    def prepare_galaxy_stage_steps(self):
        self.steps.extend([
            "",
            "FROM base as galaxy",
            "ARG ANSIBLE_GALAXY_CLI_COLLECTION_OPTS={}".format(
                self.definition.build_arg_defaults['ANSIBLE_GALAXY_CLI_COLLECTION_OPTS']
            ),
            "ARG ANSIBLE_GALAXY_CLI_ROLE_OPTS={}".format(
                self.definition.build_arg_defaults['ANSIBLE_GALAXY_CLI_ROLE_OPTS']
            ),
            "USER root",
            ""
        ])

    def prepare_build_stage_steps(self):
        if self.definition.builder_image:
            self.steps.extend([
                "",
                "FROM $EE_BUILDER_IMAGE as builder"
                "",
            ])
        else:
            # dynamic builder, create from customized base
            self.steps.extend([
                'FROM base as builder',
                'ARG PYCMD',
                'RUN $PYCMD -m pip install --no-cache-dir bindep pyyaml requirements-parser'
            ])

    def prepare_final_stage_steps(self):
        self.steps.extend([
            "",
            "FROM base",
            "USER root",
            "ARG PYCMD"  # this is consumed as an envvar by the install-from-bindep script
            "",
        ])

    def prepare_galaxy_copy_steps(self):
        if self.definition.get_dep_abs_path('galaxy'):
            self.steps.extend([
                "",
                "COPY --from=galaxy {0} {0}".format(
                    os.path.dirname(constants.base_collections_path.rstrip('/'))  # /usr/share/ansible
                ),
                "",
            ])