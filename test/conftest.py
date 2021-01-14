import yaml
from unittest import mock
import pytest
import os


@pytest.fixture(autouse=True)
def do_not_run_commands(request):
    if 'run_command' in request.keywords:
        yield
        return
    cmd_mock = mock.MagicMock(return_value=[1, [
        'python:', '  foo: []', 'system: {}',
    ]])
    with mock.patch('ansible_builder.main.run_command', new=cmd_mock):
        yield cmd_mock


@pytest.fixture(scope='session')
def data_dir():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), 'data'))


@pytest.fixture
def exec_env_definition_file(tmpdir):

    def _write_file(content=None):
        path = tmpdir.mkdir('aee').join('execution-env.yml')

        write_str = {}
        if isinstance(content, dict):
            write_str = yaml.dump(content)
        elif isinstance(content, str):
            write_str = content

        with open(path, 'w') as outfile:
            outfile.write(write_str)

        return path

    return _write_file


good_content = {'version': 1}


@pytest.fixture
def good_exec_env_definition_path(tmpdir):
    path = tmpdir.mkdir('aee').join('execution-env.yml')

    with open(path, 'w') as outfile:
        yaml.dump(good_content, outfile)

    return str(path)


@pytest.fixture
def galaxy_requirements_file(tmpdir):

    def _write_file(content={}):
        path = tmpdir.mkdir('galaxy').join('requirements.yml')

        with open(path, 'w') as outfile:
            yaml.dump(content, outfile)

        return path

    return _write_file
