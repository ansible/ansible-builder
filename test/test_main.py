import os
import pytest

from ansible_builder import __version__
from ansible_builder.main import AnsibleBuilder, UserDefinition, DefinitionError
from ansible_builder.introspect import process
from ansible_builder.requirements import sanitize_requirements


def test_version():
    assert __version__ == '0.1.0'


def test_definition_version(exec_env_definition_file):
    path = exec_env_definition_file(content={'version': 1})
    aee = AnsibleBuilder(filename=path)
    assert aee.version == '1'


def test_definition_version_missing(exec_env_definition_file):
    path = exec_env_definition_file(content={})
    aee = AnsibleBuilder(filename=path)

    with pytest.raises(ValueError):
        aee.version


@pytest.mark.parametrize('path_spec', ('absolute', 'relative'))
def test_galaxy_requirements(exec_env_definition_file, galaxy_requirements_file, path_spec, tmpdir):
    galaxy_requirements_content = {
        'collections': [
            {'name': 'geerlingguy.php_roles', 'version': '0.9.3', 'source': 'https://galaxy.ansible.com'}
        ]
    }

    galaxy_requirements_path = galaxy_requirements_file(galaxy_requirements_content)

    exec_env_content = {
        'version': 1,
        'dependencies': {
            'galaxy': str(galaxy_requirements_path) if path_spec == 'absolute' else '../galaxy/requirements.yml'
        }
    }

    exec_env_path = exec_env_definition_file(content=exec_env_content)

    aee = AnsibleBuilder(filename=exec_env_path, build_context=tmpdir.mkdir('bc'))
    aee.build()

    with open(aee.containerfile.path) as f:
        content = f.read()

    assert 'ADD requirements.yml' in content


def test_base_image(exec_env_definition_file, tmpdir):
    content = {'version': 1}
    path = exec_env_definition_file(content=content)
    aee = AnsibleBuilder(filename=path, build_context=tmpdir.mkdir('bc'))
    aee.build()

    with open(aee.containerfile.path) as f:
        content = f.read()

    assert 'ansible-runner' in content

    aee = AnsibleBuilder(filename=path, base_image='my-custom-image', build_context=tmpdir.mkdir('bc2'))
    aee.build()

    with open(aee.containerfile.path) as f:
        content = f.read()

    assert 'my-custom-image' in content


def test_build_command(exec_env_definition_file):
    content = {'version': 1}
    path = exec_env_definition_file(content=content)

    aee = AnsibleBuilder(filename=path, tag='my-custom-image')
    command = aee.build_command
    assert 'build' and 'my-custom-image' in command

    aee = AnsibleBuilder(filename=path, build_context='foo/bar/path', container_runtime='docker')

    command = aee.build_command
    assert 'foo/bar/path' in command
    assert 'foo/bar/path/Dockerfile' in " ".join(command)


@pytest.fixture
def data_dir():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), 'data'))


def test_collection_metadata(data_dir):

    files = process(data_dir)
    files['python'] = sanitize_requirements(files['python'])

    assert files == {'python': [
        'pyvcloud>=14,>=18.0.10',
        'pytz',
        'tacacs_plus'
    ], 'system': [
        'test/bindep/bindep.txt'
    ]}


def test_nested_galaxy_file(data_dir, tmpdir):
    if not os.path.exists('test/data/nested-galaxy.yml'):
        pytest.skip('Test is only valid when ran from ansible-builder root')

    bc_folder = str(tmpdir)
    AnsibleBuilder(filename='test/data/nested-galaxy.yml', build_context=bc_folder).build()

    req_in_bc = os.path.join(bc_folder, 'requirements.yml')
    assert os.path.exists(req_in_bc)

    req_original = 'test/data/foo/requirements.yml'
    with open(req_in_bc, 'r') as f_in_bc:
        with open(req_original, 'r') as f_in_def:
            assert f_in_bc.read() == f_in_def.read()


class TestDefinitionErrors:

    def test_definition_syntax_error(self, data_dir):
        path = os.path.join(data_dir, 'definition_files/bad.yml')

        with pytest.raises(DefinitionError) as error:
            AnsibleBuilder(filename=path)

        assert 'An error occured while parsing the definition file:' in str(error.value.args[0])

    @pytest.mark.parametrize('yaml_text,expect', [
        ('1', 'Definition must be a dictionary, not int'),  # integer
        (
            "{'version': 1, 'dependencies': {'python': 'Dockerfile'}}",
            'Duplicated filename Dockerfile in definition.'
        ),  # bad python file
        (
            "{'version': 1, 'dependencies': {'python': 'foo/not-exists.yml'}}",
            'not-exists.yml does not exist'
        ),  # missing file
        (
            "{'version': 1, 'additional_build_steps': 'RUN me'}",
            "Expected 'additional_build_steps' in the provided definition file to be a dictionary "
            "with keys 'prepend' and/or 'append', found a <class 'str'> instead."
        ),  # not right format for additional_build_steps
        (
            "{'version': 1, 'additional_build_steps': {'middle': 'RUN me'}}",
            "Keys ('middle',) are not allowed in 'additional_build_steps'."
        ),  # not right format for additional_build_steps
    ])
    def test_yaml_error(self, exec_env_definition_file, yaml_text, expect):
        path = exec_env_definition_file(yaml_text)
        with pytest.raises(DefinitionError) as exc:
            definition = UserDefinition(path)
            definition.validate()
        if expect:
            assert expect in exc.value.args[0]
