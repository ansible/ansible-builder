import os
import pathlib

import pytest

from ansible_builder import constants
from ansible_builder.main import AnsibleBuilder


def test_definition_version(exec_env_definition_file):
    path = exec_env_definition_file(content={'version': 1})
    aee = AnsibleBuilder(filename=path)
    assert aee.version == '1'


def test_definition_version_missing(exec_env_definition_file):
    path = exec_env_definition_file(content={})
    aee = AnsibleBuilder(filename=path)
    assert aee.version == '1'


@pytest.mark.parametrize('path_spec', ('absolute', 'relative'))
def test_galaxy_requirements(exec_env_definition_file, galaxy_requirements_file, path_spec, tmp_path):
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

    aee = AnsibleBuilder(filename=exec_env_path, build_context=str(tmp_path / 'bc'))
    aee.build()

    with open(aee.containerfile.path) as f:
        content = f.read()

    assert f'ADD {constants.user_content_subfolder} /build' in content


def test_base_image_via_build_args(exec_env_definition_file, tmp_path):
    content = {'version': 1}
    path = exec_env_definition_file(content=content)
    aee = AnsibleBuilder(filename=path, build_context=tmp_path.joinpath('bc').as_posix())
    aee.build()

    with open(aee.containerfile.path) as f:
        content = f.read()

    assert 'ansible-runner' in content

    aee = AnsibleBuilder(
        filename=path, build_args={'EE_BASE_IMAGE': 'my-custom-image'},
        build_context=tmp_path.joinpath('bc2')
    )
    aee.build()

    with open(aee.containerfile.path) as f:
        content = f.read()

    assert 'EE_BASE_IMAGE' in content  # TODO: should we make user value default?


def test_base_image_via_definition_file_build_arg(exec_env_definition_file, tmp_path):
    content = {
        'version': 1,
        'build_arg_defaults': {
            'EE_BASE_IMAGE': 'my-other-custom-image'
        }
    }
    path = exec_env_definition_file(content=content)
    aee = AnsibleBuilder(filename=path, build_context=tmp_path.joinpath('bc'))
    aee.build()

    with open(aee.containerfile.path) as f:
        content = f.read()

    assert 'EE_BASE_IMAGE=my-other-custom-image' in content


@pytest.mark.test_all_runtimes
def test_build_command(exec_env_definition_file, runtime):
    content = {'version': 1}
    path = exec_env_definition_file(content=content)

    aee = AnsibleBuilder(filename=path, tag='my-custom-image')
    command = aee.build_command
    assert 'build' and 'my-custom-image' in command

    aee = AnsibleBuilder(filename=path, build_context='foo/bar/path', container_runtime=runtime)

    command = aee.build_command
    assert 'foo/bar/path' in command
    assert 'foo/bar/path/Dockerfile' in " ".join(command)


def test_nested_galaxy_file(data_dir, tmp_path):
    if not os.path.exists('test/data/nested-galaxy.yml'):
        pytest.skip('Test is only valid when ran from ansible-builder root')

    AnsibleBuilder(filename='test/data/nested-galaxy.yml', build_context=tmp_path).build()

    req_in_bc = tmp_path.joinpath(constants.user_content_subfolder, 'requirements.yml')
    assert req_in_bc.exists()

    req_original = pathlib.Path('test/data/foo/requirements.yml')
    assert req_in_bc.read_text() == req_original.read_text()


def test_ansible_config_for_galaxy(exec_env_definition_file, tmp_path):
    if not os.path.exists('test/data/ansible-test.cfg'):
        pytest.skip('Test is only valid when ran from ansible-builder root')

    ansible_config_path = 'test/data/ansible-test.cfg'
    content = {
        'version': 1,
        'ansible_config': ansible_config_path
    }
    path = exec_env_definition_file(content=content)
    aee = AnsibleBuilder(filename=path, build_context=tmp_path.joinpath('bc'))
    aee.build()

    with open(aee.containerfile.path) as f:
        content = f.read()

    assert f'ADD {constants.user_content_subfolder}/ansible.cfg ~/.ansible.cfg' in content


@pytest.mark.test_all_runtimes
def test_use_dockerfile(exec_env_definition_file, tmp_path, runtime):
    path = exec_env_definition_file(content={'version': 1})
    aee = AnsibleBuilder(
        filename=path, build_context=tmp_path.joinpath('bc'),
        container_runtime=runtime, output_filename='Dockerfile'
    )
    aee.build()

    assert aee.containerfile.path.endswith('Dockerfile')

    with open(aee.containerfile.path) as f:
        content = f.read()

    assert 'FROM' in content
