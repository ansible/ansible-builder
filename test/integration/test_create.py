import os
import stat

import yaml

from ansible_builder import constants


def test_definition_syntax_error(cli, data_dir):
    ee_def = os.path.join(data_dir, 'definition_files', 'invalid.yml')
    r = cli(f'ansible-builder create -f {ee_def}', allow_error=True)
    assert r.rc != 0
    assert 'An error occurred while parsing the definition file' in (r.stdout + r.stderr), (r.stdout + r.stderr)


def test_missing_python_requirements_file(cli, data_dir):
    """If a user specifies a python requirements file, but we can't find it, fail sanely."""
    ee_def = os.path.join(data_dir, 'definition_files', 'no_python.yml')
    r = cli(f'ansible-builder create -f {ee_def}', allow_error=True)
    assert r.rc != 0
    assert 'does not exist' in (r.stdout + r.stderr), (r.stdout + r.stderr)


def test_missing_galaxy_requirements_file(cli, data_dir):
    """If a user specifies a galaxy requirements file, but we can't find it, fail sanely."""
    ee_def = os.path.join(data_dir, 'definition_files', 'no_galaxy.yml')
    r = cli(f'ansible-builder create -f {ee_def}', allow_error=True)
    assert r.rc != 0
    assert 'does not exist' in (r.stdout + r.stderr), (r.stdout + r.stderr)


def test_create_streams_output_with_verbosity_on(cli, build_dir_and_ee_yml):
    """Test that 'ansible-builder build' streams build output."""
    tmpdir, eeyml = build_dir_and_ee_yml("")
    result = cli(f"ansible-builder create -c {tmpdir} -f {eeyml} -v 3")
    assert 'Ansible Builder is generating your execution environment build context.' in result.stdout
    assert f'The build context can be found at: {tmpdir}' in result.stdout


def test_create_streams_output_with_verbosity_off(cli, build_dir_and_ee_yml):
    """
    Like the test_create_streams_output_with_verbosity_on test
    but making sure less output is shown with default verbosity level of 2.
    """
    tmpdir, eeyml = build_dir_and_ee_yml("")
    result = cli(f"ansible-builder create -c {tmpdir} -f {eeyml}")
    assert 'Ansible Builder is generating your execution environment build context.' not in result.stdout
    assert f'The build context can be found at: {tmpdir}' in result.stdout


def test_create_streams_output_with_invalid_verbosity(cli, build_dir_and_ee_yml):
    """
    Like the test_create_streams_output_with_verbosity_off test
    but making sure it errors out correctly with invalid verbosity level.
    """
    tmpdir, eeyml = build_dir_and_ee_yml("")
    result = cli(f"ansible-builder create -c {tmpdir} -f {eeyml} -v 6", allow_error=True)
    assert result.rc != 0
    assert f'maximum verbosity is {constants.max_verbosity}' in (result.stdout + result.stderr)


def test_inline_str_galaxy_requirements(cli, build_dir_and_ee_yml):
    """
    Ensure that galaxy requirements specified as an inline multi-line string appear in the generated build context
    """
    ee_str = """
    version: 3
    images:
      base_image:
        name: 'base_image:latest'
    dependencies:
      galaxy: |
        collections:  # a comment
        - name: community.general
        roles:
        - name: foo.bar  # another comment
    """
    tmpdir, eeyml = build_dir_and_ee_yml(ee_str)
    cli(f'ansible-builder create -c {tmpdir} -f {eeyml} --output-filename Containerfile')

    req_out = tmpdir / '_build/requirements.yml'

    assert req_out.exists()
    req_out_content = req_out.read_text()
    assert "# a comment" in req_out_content
    assert "# another comment" in req_out_content
    expected_output = {'collections': [{'name': 'community.general'}], 'roles': [{'name': 'foo.bar'}]}
    assert yaml.safe_load(req_out_content) == expected_output


def test_inline_mapping_galaxy_requirements(cli, build_dir_and_ee_yml):
    """
    Ensure that galaxy requirements specified as an inline mapping appear in the generated build context
    """
    ee_str = """
    version: 3
    images:
      base_image:
        name: 'base_image:latest'
    dependencies:
      galaxy:
        collections:
        - name: community.general
        roles:
        - name: foo.bar
    """
    tmpdir, eeyml = build_dir_and_ee_yml(ee_str)
    cli(f'ansible-builder create -c {tmpdir} -f {eeyml} --output-filename Containerfile')

    req_out = tmpdir / '_build/requirements.yml'

    assert req_out.exists()
    req_out_content = req_out.read_text()
    expected_output = {'collections': [{'name': 'community.general'}], 'roles': [{'name': 'foo.bar'}]}
    assert yaml.safe_load(req_out_content) == expected_output


def test_inline_requirements_file_perms(cli, build_dir_and_ee_yml):
    """Validate that inline requirements are written to files with proper permissions"""
    ee_str = """
    version: 3
    images:
      base_image:
        name: 'base_image:latest'
    dependencies:
      galaxy:
        collections:
        - name: community.general
      python:
        - six
      system:
        - gcc
    """
    umask = os.umask(0o777)
    os.umask(umask)

    tmpdir, eeyml = build_dir_and_ee_yml(ee_str)
    cli(f'ansible-builder create -c {tmpdir} -f {eeyml} --output-filename Containerfile')

    galaxy_req = tmpdir / f'_build/{constants.STD_GALAXY_FILENAME}'
    python_req = tmpdir / f'_build/{constants.STD_PIP_FILENAME}'
    system_req = tmpdir / f'_build/{constants.STD_BINDEP_FILENAME}'

    for out_file in (galaxy_req, python_req, system_req):
        assert out_file.exists()
        for bit in (stat.S_IRUSR, stat.S_IWUSR, stat.S_IRGRP, stat.S_IROTH):
            # If umask doesn't specifically prevent us from setting it, check that we set it
            if bit & ~umask:
                assert out_file.stat().st_mode & bit


def test_collection_verification_off(cli, build_dir_and_ee_yml):
    """
    Test that, by default, collection verification is off via the env var.
    """
    ee = [
        'dependencies:',
        '  galaxy: requirements.yml',
    ]
    req = [
        'collections:',
        '  - name: community.general',
    ]
    tmpdir, eeyml = build_dir_and_ee_yml("\n".join(ee))
    reqyml = tmpdir / "requirements.yml"
    reqyml.write_text("\n".join(req))
    cli(f'ansible-builder create -c {tmpdir} -f {eeyml} --output-filename Containerfile')

    containerfile = tmpdir / "Containerfile"
    assert containerfile.exists()
    assert "RUN ANSIBLE_GALAXY_DISABLE_GPG_VERIFY=1 ansible-galaxy" in containerfile.read_text()


def test_collection_verification_on(cli, build_dir_and_ee_yml):
    """
    Test that collection verification is on when given a keyring.
    """
    ee = [
        'dependencies:',
        '  galaxy: requirements.yml',
    ]
    req = [
        'collections:',
        '  - name: community.general',
    ]
    tmpdir, eeyml = build_dir_and_ee_yml("\n".join(ee))
    reqyml = tmpdir / "requirements.yml"
    reqyml.write_text("\n".join(req))
    keyring = tmpdir / "mykeyring.gpg"
    keyring.touch()
    cli(f'ansible-builder create -c {tmpdir} -f {eeyml} --output-filename Containerfile --galaxy-keyring {keyring}')

    containerfile = tmpdir / "Containerfile"
    assert containerfile.exists()
    text = containerfile.read_text()

    keyring_copy = tmpdir / constants.user_content_subfolder / constants.default_keyring_name
    assert keyring_copy.exists()

    assert "RUN ANSIBLE_GALAXY_DISABLE_GPG_VERIFY=1 ansible-galaxy" not in text
    assert f"--keyring \"{constants.default_keyring_name}\"" in text


def test_galaxy_signing_extra_args(cli, build_dir_and_ee_yml):
    """
    Test that all extra signing args for gpg are passed into the container file.
    """
    ee = [
        'dependencies:',
        '  galaxy: requirements.yml',
    ]
    req = [
        'collections:',
        '  - name: community.general',
    ]
    tmpdir, eeyml = build_dir_and_ee_yml("\n".join(ee))
    reqyml = tmpdir / "requirements.yml"
    reqyml.write_text("\n".join(req))
    keyring = tmpdir / "mykeyring.gpg"
    keyring.touch()
    cli(f'ansible-builder create -c {tmpdir} -f {eeyml} --output-filename Containerfile --galaxy-keyring {keyring} '
        '--galaxy-ignore-signature-status-code 500 --galaxy-required-valid-signature-count 3')

    containerfile = tmpdir / "Containerfile"
    assert containerfile.exists()
    text = containerfile.read_text()

    assert "--ignore-signature-status-code 500" in text
    assert "--required-valid-signature-count 3" in text


def test_v1v2_prepended_steps(cli, build_dir_and_ee_yml):
    """
    Tests that prepended steps are in final stage
    """
    custom_step_text = 'RUN echo "hi mom from a prepended step"'

    ee = f"""
        additional_build_steps:
          prepend: |
            {custom_step_text}
    """
    tmpdir, eeyml = build_dir_and_ee_yml(ee)
    cli(f'ansible-builder create -c {tmpdir} -f {eeyml} --output-filename Containerfile')

    containerfile = tmpdir / "Containerfile"
    assert containerfile.exists()
    text = containerfile.read_text()

    # ensure the custom step text is present and comes before the copy from build stage
    parts = text.partition(custom_step_text)
    assert parts[1] == custom_step_text
    assert "COPY --from=builder" in parts[2]


def test_v2_default_images(cli, build_dir_and_ee_yml):
    """
    Test that the base and builder images will use the defaults if not given.
    """
    ee = [
        'version: 2',
    ]
    tmpdir, eeyml = build_dir_and_ee_yml("\n".join(ee))
    cli(f'ansible-builder create -c {tmpdir} -f {eeyml} --output-filename Containerfile')

    containerfile = tmpdir / "Containerfile"
    assert containerfile.exists()
    text = containerfile.read_text()

    assert 'ARG EE_BASE_IMAGE="quay.io/ansible/ansible-runner:latest"' in text
    assert 'ARG EE_BUILDER_IMAGE="quay.io/ansible/ansible-builder:latest"' in text


def test_v2_default_base_image(cli, build_dir_and_ee_yml):
    """
    Test that the base image will use the default if not given when builder is supplied.
    Related issue: https://github.com/ansible/ansible-builder/issues/454
    """
    ee = [
        'version: 2',
        'images:',
        '  builder_image:',
        '    name: quay.io/ansible/awx-ee:latest',
    ]
    tmpdir, eeyml = build_dir_and_ee_yml("\n".join(ee))
    cli(f'ansible-builder create -c {tmpdir} -f {eeyml} --output-filename Containerfile')

    containerfile = tmpdir / "Containerfile"
    assert containerfile.exists()
    text = containerfile.read_text()

    assert 'ARG EE_BASE_IMAGE="quay.io/ansible/ansible-runner:latest"' in text
    assert 'ARG EE_BUILDER_IMAGE="quay.io/ansible/awx-ee:latest"' in text


def test_v2_default_builder_image(cli, build_dir_and_ee_yml):
    """
    Test that the builder image will use the default if not given when base is supplied.
    Related issue: https://github.com/ansible/ansible-builder/issues/454
    """
    ee = [
        'version: 2',
        'images:',
        '  base_image:',
        '    name: quay.io/ansible/awx-ee:latest',
    ]
    tmpdir, eeyml = build_dir_and_ee_yml("\n".join(ee))
    cli(f'ansible-builder create -c {tmpdir} -f {eeyml} --output-filename Containerfile')

    containerfile = tmpdir / "Containerfile"
    assert containerfile.exists()
    text = containerfile.read_text()

    assert 'ARG EE_BASE_IMAGE="quay.io/ansible/awx-ee:latest"' in text
    assert 'ARG EE_BUILDER_IMAGE="quay.io/ansible/ansible-builder:latest"' in text


def test_v3_pre_post_commands(cli, data_dir, tmp_path):
    """Test that the pre/post commands are inserted"""
    ee_def = data_dir / 'v3' / 'pre_and_post' / 'ee.yml'
    r = cli(f'ansible-builder create -c {str(tmp_path)} -f {ee_def} --output-filename Containerfile')
    assert r.rc == 0

    containerfile = tmp_path / "Containerfile"
    assert containerfile.exists()
    text = containerfile.read_text()

    assert "ARG PRE_BASE1\n" in text
    assert "ARG PRE_BASE2\n" in text
    assert "ARG POST_BASE1\n" in text
    assert "ARG POST_BASE2\n" in text
    assert "ARG PRE_GALAXY" in text
    assert "ARG POST_GALAXY" in text
    assert "ARG PRE_BUILDER" in text
    assert "ARG POST_BUILDER" in text
    assert "ARG PRE_FINAL" in text
    assert "ARG POST_FINAL" in text


def test_v3_complete(cli, data_dir, tmp_path):
    """For testing various elements in a complete v2 EE file"""
    ee_def = data_dir / 'v3' / 'complete' / 'ee.yml'
    r = cli(f'ansible-builder create -c {str(tmp_path)} -f {ee_def} --output-filename Containerfile')
    assert r.rc == 0

    containerfile = tmp_path / "Containerfile"
    assert containerfile.exists()
    text = containerfile.read_text()

    assert 'ARG EE_BASE_IMAGE="registry.redhat.io/ansible-automation-platform-21/ee-minimal-rhel8:latest"\n' in text
    assert 'ARG EE_BUILDER_IMAGE' not in text
    assert 'ARG PYCMD="/usr/local/bin/mypython"\n' in text
    assert 'ARG PYPKG="mypython3"\n' in text
    assert 'ARG ANSIBLE_GALAXY_CLI_COLLECTION_OPTS="--foo"\n' in text
    assert 'ARG ANSIBLE_GALAXY_CLI_ROLE_OPTS="--bar"\n' in text
    assert 'ARG ANSIBLE_INSTALL_REFS="ansible-core==2.13 ansible-runner==2.3.1"\n' in text

    # verify that the ansible-galaxy command check is performed
    assert 'RUN /output/scripts/check_galaxy' in text

    # verify that the ansible/runner check is performed
    assert 'RUN /output/scripts/check_ansible' in text

    # /output should be removed in final image
    assert 'RUN rm -rf /output' in text

    # verify that the default init is being installed and that ENTRYPOINT is set
    assert "RUN $PYCMD -m pip install --no-cache-dir 'dumb-init==" in text
    assert 'WORKDIR /runner' in text
    assert 'RUN chmod ug+rw /etc/passwd' in text
    assert 'RUN mkdir -p /runner' in text
    assert f'ENTRYPOINT ["{constants.FINAL_IMAGE_BIN_PATH}/entrypoint", "dumb-init"]' in text
    assert 'USER 1001' in text

    # check additional_build_files
    myconfigs_path = tmp_path / constants.user_content_subfolder / "myconfigs"
    assert myconfigs_path.is_dir()
    random_file = myconfigs_path / "random.cfg"
    assert random_file.exists()

    # Tree structure we expect:
    # ├── mydata
    # │   ├── a.dat
    # │   └── text_files
    # │       ├── a.txt

    mydata_path = tmp_path / constants.user_content_subfolder / "mydata"
    assert mydata_path.is_dir()
    dat_file = mydata_path / "a.dat"
    assert dat_file.exists()
    text_files = mydata_path / "text_files"
    assert text_files.is_dir()
    a_text = text_files / "a.txt"
    assert a_text.exists()


def test_v3_skip_ansible_check(cli, build_dir_and_ee_yml):
    """
    Test 'options.skip_ansible_check' works.
    """
    ee = [
        'version: 3',
        'images:',
        '  base_image:',
        '    name: quay.io/ansible/awx-ee:latest',
        'options:',
        '  skip_ansible_check: True',
    ]

    tmpdir, eeyml = build_dir_and_ee_yml("\n".join(ee))
    cli(f'ansible-builder create -c {tmpdir} -f {eeyml} --output-filename Containerfile')

    containerfile = tmpdir / "Containerfile"
    assert containerfile.exists()
    text = containerfile.read_text()

    assert "check_ansible" not in text


def test_v3_skip_container_init(cli, build_dir_and_ee_yml):
    tmpdir, eeyml = build_dir_and_ee_yml(
        """
        version: 3
        images:
          base_image:
            name: quay.io/ansible/awx-ee:latest
        options:
          container_init: {}
        """
    )
    cli(f'ansible-builder create -c {tmpdir} -f {eeyml} --output-filename Containerfile')

    containerfile = tmpdir / "Containerfile"
    assert containerfile.exists()
    text = containerfile.read_text()

    assert "dumb-init" not in text
    assert "ENTRYPOINT" not in text
    assert 'CMD ["bash"]' not in text


def test_v3_custom_container_init(cli, build_dir_and_ee_yml):
    tmpdir, eeyml = build_dir_and_ee_yml(
        """
        version: 3
        images:
          base_image:
            name: quay.io/ansible/awx-ee:latest
        options:
          container_init:
            package_pip: custominit==1.2.3
            entrypoint: |
              ["custominit"]
            cmd: |
              ["customcmd"]
        """
    )
    cli(f'ansible-builder create -c {tmpdir} -f {eeyml} --output-filename Containerfile')

    containerfile = tmpdir / "Containerfile"
    assert containerfile.exists()
    text = containerfile.read_text()

    assert "pip install --no-cache-dir 'custominit==1.2.3'" in text
    assert 'ENTRYPOINT ["custominit"]' in text
    assert 'CMD ["customcmd"]' in text


def test_v3_no_relax_passwd_perms(cli, build_dir_and_ee_yml):
    """
    Test that disabling 'options.relax_passwd_permissions' works.
    """
    ee = """
    version: 3
    images:
      base_image:
        name: quay.io/ansible/awx-ee:latest
    options:
        relax_passwd_permissions: false
    """

    tmpdir, eeyml = build_dir_and_ee_yml(ee)
    cli(f'ansible-builder create -c {tmpdir} -f {eeyml} --output-filename Containerfile')

    containerfile = tmpdir / "Containerfile"
    assert containerfile.exists()
    text = containerfile.read_text()

    assert "/etc/passwd" not in text


def test_v3_custom_workdir(cli, build_dir_and_ee_yml):
    """
    Test that a custom 'options.workdir' creates the dir and sets it
    """
    ee = """
    version: 3
    images:
      base_image:
        name: quay.io/ansible/awx-ee:latest
    options:
        workdir: /yourmom
    """

    tmpdir, eeyml = build_dir_and_ee_yml(ee)
    cli(f'ansible-builder create -c {tmpdir} -f {eeyml} --output-filename Containerfile')

    containerfile = tmpdir / "Containerfile"
    assert containerfile.exists()
    text = containerfile.read_text()

    assert "WORKDIR /yourmom" in text
    assert "mkdir -p /yourmom && chgrp 0 /yourmom && chmod -R ug+rwx /yourmom" in text


def test_v3_no_workdir(cli, build_dir_and_ee_yml):
    """
    Test that empty 'options.workdir' skips the setting and creation of the default.
    """
    ee = """
    version: 3
    images:
      base_image:
        name: quay.io/ansible/awx-ee:latest
    options:
        workdir:
    """

    tmpdir, eeyml = build_dir_and_ee_yml(ee)
    cli(f'ansible-builder create -c {tmpdir} -f {eeyml} --output-filename Containerfile')

    containerfile = tmpdir / "Containerfile"
    assert containerfile.exists()
    text = containerfile.read_text()

    assert "WORKDIR" not in text.replace('WORKDIR /build', '')  # intermediate stages set WORKDIR- ignore those
    assert "mkdir -p /runner" not in text


def test_v3_set_user_id(cli, build_dir_and_ee_yml):
    """
    Test that a custom 'options.user' sets it
    """
    tmpdir, eeyml = build_dir_and_ee_yml(
        """
        version: 3
        images:
          base_image:
            name: quay.io/ansible/awx-ee:latest
        options:
          user: bob
        """
    )
    cli(f'ansible-builder create -c {tmpdir} -f {eeyml} --output-filename Containerfile')

    containerfile = tmpdir / "Containerfile"
    assert containerfile.exists()
    text = containerfile.read_text()

    assert "USER bob" in text


def test_v3_additional_build_files(cli, build_dir_and_ee_yml):
    """
    Test functionality of addition_build_files.
    """
    tmpdir, eeyml = build_dir_and_ee_yml(
        """
        version: 3
        additional_build_files:
          - src: ansible.cfg
            dest: configs
        """
    )

    cfg = tmpdir / 'ansible.cfg'
    cfg.touch()

    cli(f'ansible-builder create -c {tmpdir} -f {eeyml} --output-filename Containerfile')


def test_exclude_files_created(cli, build_dir_and_ee_yml):
    """
    Test that the bindep and Python requirement exclude files are created.
    """
    tmpdir, eeyml = build_dir_and_ee_yml(
        """
        version: 3
        images:
          base_image:
            name: quay.io/ansible/awx-ee:latest
        dependencies:
          galaxy:
            collections:
              - name: community.crypto
          exclude:
            python:
              - pyyaml
            system:
              - openssh-client
            all_from_collections:
              - a.b
        """
    )

    cli(f'ansible-builder create -c {tmpdir} -f {eeyml} --output-filename Containerfile')

    # Validate that the bindep exclude file is created with proper content
    bindep_exclude = tmpdir / constants.user_content_subfolder / f"exclude-{constants.STD_BINDEP_FILENAME}"
    assert bindep_exclude.exists()
    text = bindep_exclude.read_text()
    assert text == "openssh-client"

    # Validate that the Python requirements exclude file is created with proper content
    pyreq_exclude = tmpdir / constants.user_content_subfolder / f"exclude-{constants.STD_PIP_FILENAME}"
    assert pyreq_exclude.exists()
    text = pyreq_exclude.read_text()
    assert text == "pyyaml"

    # Validate that the collections exclude file is created with proper content
    coll_exclude = tmpdir / constants.user_content_subfolder / f"{constants.EXCL_COLLECTIONS_FILENAME}"
    assert coll_exclude.exists()
    text = coll_exclude.read_text()
    assert text == "a.b"

    # Validate that the EE will use the exclude files
    containerfile = tmpdir / "Containerfile"
    assert containerfile.exists()
    text = containerfile.read_text()
    expected_introspect_command = "RUN $PYCMD /output/scripts/introspect.py introspect" \
                                  f" --exclude-pip-reqs=exclude-{constants.STD_PIP_FILENAME}" \
                                  f" --exclude-bindep-reqs=exclude-{constants.STD_BINDEP_FILENAME}" \
                                  f" --exclude-collection-reqs={constants.EXCL_COLLECTIONS_FILENAME}" \
                                  " --write-bindep=/tmp/src/bindep.txt --write-pip=/tmp/src/requirements.txt\n"
    assert expected_introspect_command in text
