import pytest

from ansible_builder import __version__
from ansible_builder.main import AnsibleBuilder


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


def test_galaxy_requirements(exec_env_definition_file, galaxy_requirements_file):
    galaxy_requirements_content = {
        'collections': [
            {'name': 'geerlingguy.php_roles', 'version': '0.9.3', 'source': 'https://galaxy.ansible.com'}
        ]
    }

    galaxy_requirements_path = galaxy_requirements_file(galaxy_requirements_content)

    exec_env_content = {
        'version': 1,
        'dependencies': {
            'galaxy': str(galaxy_requirements_path)
        }
    }

    exec_env_path = exec_env_definition_file(content=exec_env_content)

    aee = AnsibleBuilder(filename=exec_env_path)
    aee.create()

    with open(aee.containerfile.path) as f:
        content = f.read()

    assert 'ADD requirements.yml' in content


def test_base_image(exec_env_definition_file):
    content = {
        'version': 1
    }
    path = exec_env_definition_file(content=content)
    aee = AnsibleBuilder(filename=path)
    aee.create()

    with open(aee.containerfile.path) as f:
        content = f.read()

    assert 'ansible-runner' in content

    aee = AnsibleBuilder(filename=path, base_image='my-custom-image')
    aee.create()

    with open(aee.containerfile.path) as f:
        content = f.read()

    assert 'my-custom-image' in content
