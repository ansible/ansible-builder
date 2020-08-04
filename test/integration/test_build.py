import pytest


def test_build_fail_exitcode():
    """Test that when a build fails, the ansible-builder exits with non-zero exit code.

    Example: https://github.com/ansible/ansible-builder/issues/51
    """
    pytest.skip("Not implemented")


def test_missing_python_requirements_file():
    """If a user specifies a python requirements file, but we can't find it, fail sanely."""
    pytest.skip("Not implemented")


def test_missing_galaxy_requirements_file():
    """If a user specifies a galaxy requirements file, but we can't find it, fail sanely."""
    pytest.skip("Not implemented")


def test_build_streams_output(cli, build_dir_and_ee_yml, ee_tag):
    """Test that 'ansible-builder build' streams build output."""
    tmpdir, eeyml = build_dir_and_ee_yml("")
    result = cli(f"ansible-builder build -c {tmpdir} -f {eeyml} -t {ee_tag}")
    assert f"podman build -f {tmpdir}/Containerfile" in result.stdout
    assert f"The build context can be found at: {tmpdir}" in result.stdout
