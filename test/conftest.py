import yaml
from unittest import mock
import pytest


@pytest.fixture(autouse=True)
def do_not_run_commands():
    cmd_mock = mock.MagicMock(return_value=[1, []])
    with mock.patch('ansible_builder.main.run_command', new=cmd_mock):
        yield cmd_mock


@pytest.fixture
def exec_env_definition_file(tmpdir):

    def _write_file(content={}):
        path = tmpdir.mkdir('aee').join('execution-env.yml')

        with open(path, 'w') as outfile:
            yaml.dump(content, outfile)

        return path

    return _write_file


good_content = {'version': 1}


@pytest.fixture
def good_exec_env_definition_path(tmpdir):
    path = tmpdir.mkdir('aee').join('execution-env.yml')

    with open(path, 'w') as outfile:
        yaml.dump(good_content, outfile)

    return path


@pytest.fixture
def galaxy_requirements_file(tmpdir):

    def _write_file(content={}):
        path = tmpdir.mkdir('galaxy').join('requirements.yml')

        with open(path, 'w') as outfile:
            yaml.dump(content, outfile)

        return path

    return _write_file
