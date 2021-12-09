import pathlib

import pytest
import yaml


@pytest.fixture(autouse=True)
def do_not_run_commands(request, mocker):
    if 'run_command' in request.keywords:
        yield
        return
    cmd_mock = mocker.MagicMock(return_value=[1, [
        'python:', '  foo: []', 'system: {}',
    ]])
    mocker.patch('ansible_builder.main.run_command', new=cmd_mock)
    yield cmd_mock


@pytest.fixture(scope='session')
def data_dir():
    return pathlib.Path(pathlib.Path(__file__).parent).joinpath('data')


@pytest.fixture
def exec_env_definition_file(tmp_path):

    def _write_file(content=None):
        path = tmp_path / 'aee'
        path.mkdir()
        path = path / 'execution-env.yml'

        write_str = {}
        if isinstance(content, dict):
            write_str = yaml.dump(content)
        elif isinstance(content, str):
            write_str = content

        path.write_text(write_str)

        return path

    return _write_file


good_content = {'version': 1}


@pytest.fixture
def good_exec_env_definition_path(tmp_path):
    path = tmp_path / 'aee'
    path.mkdir()
    path = path / 'execution-env.yml'

    with path.open('w') as outfile:
        yaml.dump(good_content, outfile)

    return path


@pytest.fixture
def galaxy_requirements_file(tmp_path):

    def _write_file(content={}):
        path = tmp_path / 'galaxy'
        path.mkdir()
        path = path / 'requirements.yml'

        with path.open('w') as outfile:
            yaml.dump(content, outfile)

        return path

    return _write_file
