import os


def test_definition_syntax_error(cli, data_dir):
    ee_def = os.path.join(data_dir, 'definition_files', 'invalid.yml')
    r = cli(f'ansible-builder create -f {ee_def}', allow_error=True)
    assert r.rc != 0
    assert 'An error occured while parsing the definition file' in (r.stdout + r.stderr), (r.stdout + r.stderr)


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
