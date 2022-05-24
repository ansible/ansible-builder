import os

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
    Like the test_create_streams_output_with_verbosity_on test but making sure less output is shown with default verbosity level of 2.
    """
    tmpdir, eeyml = build_dir_and_ee_yml("")
    result = cli(f"ansible-builder create -c {tmpdir} -f {eeyml}")
    assert 'Ansible Builder is generating your execution environment build context.' not in result.stdout
    assert f'The build context can be found at: {tmpdir}' in result.stdout


def test_create_streams_output_with_invalid_verbosity(cli, build_dir_and_ee_yml):
    """
    Like the test_create_streams_output_with_verbosity_off test but making sure it errors out correctly with invalid verbosity level.
    """
    tmpdir, eeyml = build_dir_and_ee_yml("")
    result = cli(f"ansible-builder create -c {tmpdir} -f {eeyml} -v 6", allow_error=True)
    assert result.rc != 0
    assert 'invalid choice: 6 (choose from 0, 1, 2, 3)' in (result.stdout + result.stderr)


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
    Test that all extr asigning args for gpg are passed into the container file.
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
