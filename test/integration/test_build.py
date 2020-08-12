import pytest
import os


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


def test_build_streams_output(cli, container_runtime, build_dir_and_ee_yml, ee_tag):
    """Test that 'ansible-builder build' streams build output."""
    tmpdir, eeyml = build_dir_and_ee_yml("")
    result = cli(f"ansible-builder build -c {tmpdir} -f {eeyml} -t {ee_tag} --container-runtime {container_runtime}")
    assert f"{container_runtime} build -f {tmpdir}" in result.stdout
    assert f"The build context can be found at: {tmpdir}" in result.stdout


def test_user_system_requirement(cli, container_runtime, ee_tag, tmpdir, data_dir):
    bc = str(tmpdir)
    ee_def = os.path.join(data_dir, 'subversion', 'execution-environment.yml')
    cli(
        f'ansible-builder build -c {bc} -f {ee_def} -t {ee_tag} --container-runtime {container_runtime}'
    )
    result = cli(
        f'{container_runtime} run --rm {ee_tag} svn --help'
    )
    assert 'Subversion is a tool for version control' in result.stdout


class TestPytz:

    @pytest.fixture(scope='class')
    def pytz(self, cli_class, container_runtime, ee_tag, data_dir, tmpdir_factory):
        bc_folder = str(tmpdir_factory.mktemp('bc'))
        ee_def = os.path.join(data_dir, 'pytz', 'execution-environment.yml')
        r = cli_class(
            f'ansible-builder build -c {bc_folder} -f {ee_def} -t {ee_tag} --container-runtime {container_runtime}'
        )
        assert 'Collecting pytz (from -r /build/requirements.txt' in r.stdout, r.stdout
        return (ee_tag, bc_folder)

    def test_has_pytz(self, cli, container_runtime, pytz):
        ee_tag, bc_folder = pytz
        r = cli(f'{container_runtime} run --rm {ee_tag} pip3 show pytz')
        assert 'World timezone definitions, modern and historical' in r.stdout

    def test_build_layer_reuse(self, cli, container_runtime, data_dir, pytz):
        ee_tag, bc_folder = pytz
        ee_def = os.path.join(data_dir, 'pytz', 'execution-environment.yml')
        if container_runtime == 'podman':
            pytest.skip('Active issue, see https://github.com/ansible/ansible-builder/issues/69')
        r = cli(
            f'ansible-builder build -c {bc_folder} -f {ee_def} -t {ee_tag} --container-runtime {container_runtime}'
        )
        assert 'Collecting pytz (from -r /build/requirements.txt' not in r.stdout, r.stdout
        assert 'ADD requirements.txt /build/\n ---> Using cache' in r.stdout, r.stdout
