import os

from ansible_builder import constants
from ansible_builder.containerfile import Containerfile
from ansible_builder.user_definition import UserDefinition

# pylint: disable=W0212


def make_containerfile(tmpdir, ee_path, run_validate=False, **cf_kwargs):
    definition = UserDefinition(ee_path)
    if run_validate:
        definition.validate()
    c = Containerfile(definition, build_context=str(tmpdir), container_runtime='podman', **cf_kwargs)
    return c


def test_insert_custom_steps_list(build_dir_and_ee_yml):
    ee_data = [
        'additional_build_steps:',
        '  prepend:',
        '    - RUN echo This is the custom steps list test',
        '    - RUN whoami',
    ]

    tmpdir, ee_path = build_dir_and_ee_yml("\n".join(ee_data))
    c = make_containerfile(tmpdir, ee_path)
    c._insert_custom_steps("prepend")
    assert c.steps == ['RUN echo This is the custom steps list test', 'RUN whoami']


def test_insert_custom_steps_string(build_dir_and_ee_yml):
    ee_data = [
        'additional_build_steps:',
        '  append: |',
        '    RUN echo This is the custom steps string test',
        '    RUN whoami',
    ]

    tmpdir, ee_path = build_dir_and_ee_yml("\n".join(ee_data))
    c = make_containerfile(tmpdir, ee_path)
    c._insert_custom_steps("append")
    assert c.steps == ['RUN echo This is the custom steps string test', 'RUN whoami']


def test_prepare_galaxy_install_steps(build_dir_and_ee_yml):
    ee_data = [
        'dependencies:',
        '  galaxy: requirements.yml',
    ]
    tmpdir, ee_path = build_dir_and_ee_yml("\n".join(ee_data))
    c = make_containerfile(tmpdir, ee_path)
    c._prepare_galaxy_install_steps()
    expected = [
        f"RUN mkdir -p {os.path.dirname(constants.base_collections_path.rstrip('/'))}",
        f"RUN ansible-galaxy role install $ANSIBLE_GALAXY_CLI_ROLE_OPTS "
        f"-r {constants.STD_GALAXY_FILENAME} --roles-path \"{constants.base_roles_path}\"",
        f"RUN ANSIBLE_GALAXY_DISABLE_GPG_VERIFY=1 ansible-galaxy collection install "
        f"$ANSIBLE_GALAXY_CLI_COLLECTION_OPTS -r {constants.STD_GALAXY_FILENAME} "
        f"--collections-path \"{constants.base_collections_path}\""
    ]
    assert c.steps == expected


def test_prepare_galaxy_install_steps_with_keyring(build_dir_and_ee_yml):
    ee_data = [
        'dependencies:',
        '  galaxy: requirements.yml',
    ]
    tmpdir, ee_path = build_dir_and_ee_yml("\n".join(ee_data))
    c = make_containerfile(tmpdir, ee_path, galaxy_keyring=constants.default_keyring_name)
    c._prepare_galaxy_install_steps()
    expected = [
        f"RUN mkdir -p {os.path.dirname(constants.base_collections_path.rstrip('/'))}",
        f"RUN ansible-galaxy role install $ANSIBLE_GALAXY_CLI_ROLE_OPTS "
        f"-r {constants.STD_GALAXY_FILENAME} --roles-path \"{constants.base_roles_path}\"",
        f"RUN ansible-galaxy collection install $ANSIBLE_GALAXY_CLI_COLLECTION_OPTS "
        f"-r {constants.STD_GALAXY_FILENAME} "
        f"--collections-path \"{constants.base_collections_path}\" --keyring \"{constants.default_keyring_name}\""
    ]
    assert c.steps == expected


def test_prepare_galaxy_install_steps_with_sigcount(build_dir_and_ee_yml):
    sig_count = 3
    ee_data = [
        'dependencies:',
        '  galaxy: requirements.yml',
    ]
    tmpdir, ee_path = build_dir_and_ee_yml("\n".join(ee_data))
    c = make_containerfile(tmpdir, ee_path,
                           galaxy_keyring=constants.default_keyring_name,
                           galaxy_required_valid_signature_count=sig_count)
    c._prepare_galaxy_install_steps()
    expected = [
        f"RUN mkdir -p {os.path.dirname(constants.base_collections_path.rstrip('/'))}",
        f"RUN ansible-galaxy role install $ANSIBLE_GALAXY_CLI_ROLE_OPTS "
        f"-r {constants.STD_GALAXY_FILENAME} --roles-path \"{constants.base_roles_path}\"",
        f"RUN ansible-galaxy collection install $ANSIBLE_GALAXY_CLI_COLLECTION_OPTS "
        f"-r {constants.STD_GALAXY_FILENAME} "
        f"--collections-path \"{constants.base_collections_path}\" "
        f"--required-valid-signature-count {sig_count} --keyring \"{constants.default_keyring_name}\""
    ]
    assert c.steps == expected


def test_prepare_galaxy_install_steps_with_ignore_code(build_dir_and_ee_yml):
    codes = [1, 2]
    ee_data = [
        'dependencies:',
        '  galaxy: requirements.yml',
    ]
    tmpdir, ee_path = build_dir_and_ee_yml("\n".join(ee_data))
    c = make_containerfile(tmpdir, ee_path,
                           galaxy_keyring=constants.default_keyring_name,
                           galaxy_ignore_signature_status_codes=codes)
    c._prepare_galaxy_install_steps()
    expected = [
        f"RUN mkdir -p {os.path.dirname(constants.base_collections_path.rstrip('/'))}",
        f"RUN ansible-galaxy role install $ANSIBLE_GALAXY_CLI_ROLE_OPTS "
        f"-r {constants.STD_GALAXY_FILENAME} --roles-path \"{constants.base_roles_path}\"",
        f"RUN ansible-galaxy collection install $ANSIBLE_GALAXY_CLI_COLLECTION_OPTS "
        f"-r {constants.STD_GALAXY_FILENAME} "
        f"--collections-path \"{constants.base_collections_path}\" "
        f"--ignore-signature-status-code {codes[0]} --ignore-signature-status-code {codes[1]} "
        f"--keyring \"{constants.default_keyring_name}\""
    ]
    assert c.steps == expected


def test_v2_custom_builder_image(build_dir_and_ee_yml):
    """
    Test that a customer builder image in the v2 schema is used (not valid for v3).
    """
    ee_data = """
    version: 2
    images:
      base_image:
        name: quay.io/user/mycustombaseimage:latest
      builder_image:
        name: quay.io/user/mycustombuilderimage:latest
    """
    tmpdir, ee_path = build_dir_and_ee_yml(ee_data)
    c = make_containerfile(tmpdir, ee_path, run_validate=True)
    c.prepare()

    assert 'ARG EE_BUILDER_IMAGE="quay.io/user/mycustombuilderimage:latest"' in c.steps
    assert "FROM $EE_BUILDER_IMAGE as builder" in c.steps


def test_v3_various(build_dir_and_ee_yml):
    """
    Test various v3 expected outputs appear in the Containerfile as they
    happen during the prepare() phase. These could be broken down into
    individual tests, but for now we'll just use this catch-all.
    """
    ee_data = """
    version: 3
    images:
      base_image:
        name: quay.io/user/mycustombaseimage:latest
    options:
      skip_ansible_check: False
      relax_passwd_permissions: True
      workdir: /myworkdir
      container_init:
        package_pip: dumb-init==x.y.z
        entrypoint: '["dumb-init"]'
        cmd: '["csh"]'
      user: myuser
    dependencies:
      ansible_core:
        package_pip: ansible-core
      python_interpreter:
        package_system: python310
    """
    tmpdir, ee_path = build_dir_and_ee_yml(ee_data)
    c = make_containerfile(tmpdir, ee_path, run_validate=True)
    c.prepare()

    assert "RUN /output/scripts/check_ansible $PYCMD" in c.steps
    assert "RUN chmod ug+rw /etc/passwd" in c.steps
    assert "RUN mkdir -p /myworkdir && chgrp 0 /myworkdir && chmod -R ug+rwx /myworkdir" in c.steps
    assert "RUN $PYCMD -m pip install --no-cache-dir 'dumb-init==x.y.z'" in c.steps
    assert "USER myuser" in c.steps
    assert "RUN $PKGMGR install $PYPKG -y ; if [ -z $PKGMGR_PRESERVE_CACHE ]; then $PKGMGR clean all; fi" in c.steps
    assert "RUN $PYCMD -m pip install --no-cache-dir $ANSIBLE_INSTALL_REFS" in c.steps
    assert 'ENTRYPOINT ["dumb-init"]' in c.steps
    assert 'CMD ["csh"]' in c.steps


def test__handle_additional_build_files(build_dir_and_ee_yml):
    """
    Test additional build file handling works as expected.
    """
    ee_data = """
    version: 3
    images:
      base_image:
        name: quay.io/user/mycustombaseimage:latest
    additional_build_files:
      - src: ansible.cfg
        dest: configs
    """
    tmpdir, ee_path = build_dir_and_ee_yml(ee_data)

    cfg = tmpdir / 'ansible.cfg'
    cfg.touch()

    c = make_containerfile(tmpdir, ee_path, run_validate=True)
    c._handle_additional_build_files()

    config_dir = tmpdir / '_build' / 'configs'
    assert config_dir.exists()
    assert (config_dir / 'ansible.cfg').exists()


def test_pep668_v1(build_dir_and_ee_yml):
    """
    Test PEP668 handling with v1 format.
    """
    ee_data = """
    version: 1
    """
    tmpdir, ee_path = build_dir_and_ee_yml(ee_data)
    c = make_containerfile(tmpdir, ee_path, run_validate=True)
    c.prepare()
    assert "ENV PIP_BREAK_SYSTEM_PACKAGES=1" in c.steps
    assert "RUN /output/scripts/pip_install $PYCMD" in c.steps


def test_pep668_v2(build_dir_and_ee_yml):
    """
    Test PEP668 handling with v2 format.
    """
    ee_data = """
    version: 2
    images:
      base_image:
        name: quay.io/user/mycustombaseimage:latest
      builder_image:
        name: quay.io/user/mycustombuilderimage:latest
    """
    tmpdir, ee_path = build_dir_and_ee_yml(ee_data)
    c = make_containerfile(tmpdir, ee_path, run_validate=True)
    c.prepare()
    assert "ENV PIP_BREAK_SYSTEM_PACKAGES=1" in c.steps
    assert "RUN /output/scripts/pip_install $PYCMD" in c.steps


def test_pep668_v3(build_dir_and_ee_yml):
    """
    Test PEP668 handling with v3 format.
    """
    ee_data = """
    version: 3
    images:
      base_image:
        name: quay.io/user/mycustombaseimage:latest
    """
    tmpdir, ee_path = build_dir_and_ee_yml(ee_data)
    c = make_containerfile(tmpdir, ee_path, run_validate=True)
    c.prepare()
    assert "ENV PIP_BREAK_SYSTEM_PACKAGES=1" in c.steps
    assert "RUN /output/scripts/pip_install $PYCMD" in c.steps


def test_pep668_v3_skip_pip_install(build_dir_and_ee_yml):
    """
    Test PEP668 handling with v3 format and skipping pip installation.
    """
    ee_data = """
    version: 3
    images:
      base_image:
        name: quay.io/user/mycustombaseimage:latest
    options:
      skip_pip_install: True
    """
    tmpdir, ee_path = build_dir_and_ee_yml(ee_data)
    c = make_containerfile(tmpdir, ee_path, run_validate=True)
    c.prepare()
    assert "ENV PIP_BREAK_SYSTEM_PACKAGES=1" in c.steps
    assert "RUN /output/scripts/pip_install $PYCMD" not in c.steps


def test_v1_builder_image(build_dir_and_ee_yml):
    """
    Test for issue 646 (https://github.com/ansible/ansible-builder/issues/646).
    Also test that pip_install is installed into the custom builder image.
    """
    ee_data = """
    version: 1
    """
    tmpdir, ee_path = build_dir_and_ee_yml(ee_data)
    c = make_containerfile(tmpdir, ee_path, run_validate=True)
    c.prepare()
    assert "FROM $EE_BUILDER_IMAGE as builder" in c.steps
    assert "COPY _build/scripts/pip_install /output/scripts/pip_install" in c.steps
    assert "RUN /output/scripts/pip_install $PYCMD" in c.steps


def test_v2_builder_image(build_dir_and_ee_yml):
    """
    Test that pip_install is installed into the custom v2 builder image.
    """
    ee_data = """
    version: 2
    images:
      base_image:
        name: quay.io/user/mycustombaseimage:latest
      builder_image:
        name: quay.io/user/mycustombuilderimage:latest
    """
    tmpdir, ee_path = build_dir_and_ee_yml(ee_data)
    c = make_containerfile(tmpdir, ee_path, run_validate=True)
    c.prepare()
    assert "FROM $EE_BUILDER_IMAGE as builder" in c.steps
    assert "COPY _build/scripts/pip_install /output/scripts/pip_install" in c.steps
    assert "RUN /output/scripts/pip_install $PYCMD" in c.steps


def test_v2_builder_image_default(build_dir_and_ee_yml):
    """
    Test that pip_install is NOT installed into the builder image when not defined.
    """
    ee_data = """
    version: 2
    images:
      base_image:
        name: quay.io/user/mycustombaseimage:latest
    """
    tmpdir, ee_path = build_dir_and_ee_yml(ee_data)
    c = make_containerfile(tmpdir, ee_path, run_validate=True)
    c.prepare()
    assert "FROM base as builder" in c.steps
    assert "COPY _build/scripts/pip_install /output/scripts/pip_install" not in c.steps


def test_prepare_introspect_assemble_steps(build_dir_and_ee_yml):
    """
    Test that the introspect command is built as expected.
    """

    ee_data = """
    version: 3
    images:
      base_image:
        name: quay.io/user/mycustombaseimage:latest
    dependencies:
        python:
           - six
        system:
           - git
        galaxy:
           collections:
              - name: community.windows
        exclude:
           python:
             - aaa
           system:
             - bbb
           all_from_collections:
             - a.b
    """

    tmpdir, ee_path = build_dir_and_ee_yml(ee_data)
    c = make_containerfile(tmpdir, ee_path, run_validate=True)
    c._create_folder_copy_files()
    c._prepare_introspect_assemble_steps()

    expected_introspect_command = "RUN $PYCMD /output/scripts/introspect.py introspect" \
                                  f" --user-pip={constants.STD_PIP_FILENAME}" \
                                  f" --exclude-pip-reqs=exclude-{constants.STD_PIP_FILENAME}" \
                                  f" --user-bindep={constants.STD_BINDEP_FILENAME}" \
                                  f" --exclude-bindep-reqs=exclude-{constants.STD_BINDEP_FILENAME}" \
                                  f" --exclude-collection-reqs={constants.EXCL_COLLECTIONS_FILENAME}" \
                                  " --write-bindep=/tmp/src/bindep.txt --write-pip=/tmp/src/requirements.txt"
    assert expected_introspect_command in c.steps
