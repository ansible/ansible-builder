import os
import pytest

from ansible_builder import constants
from ansible_builder.main import AnsibleBuilder
from ansible_builder.cli import parse_args
from ansible_builder.policies import PolicyChoices


def prepare(args):
    args = parse_args(args)
    return AnsibleBuilder(**vars(args))


def test_custom_image(exec_env_definition_file, tmp_path):
    content = {'version': 1}
    path = str(exec_env_definition_file(content=content))

    aee = prepare(['build', '-f', path, '--build-arg', 'EE_BASE_IMAGE=my-custom-image', '-c', str(tmp_path)])
    assert aee.build_args == {'EE_BASE_IMAGE': 'my-custom-image'}


def test_custom_ansible_galaxy_cli_collection_opts(exec_env_definition_file, tmp_path):
    content = {'version': 1}
    path = str(exec_env_definition_file(content=content))

    aee = prepare(['build', '-f', path, '--build-arg', 'ANSIBLE_GALAXY_CLI_COLLECTION_OPTS=--pre', '-c', str(tmp_path)])
    assert aee.build_args == {'ANSIBLE_GALAXY_CLI_COLLECTION_OPTS': '--pre'}


def test_custom_ansible_galaxy_cli_role_opts(exec_env_definition_file, tmp_path):
    content = {'version': 1}
    path = str(exec_env_definition_file(content=content))

    aee = prepare(['build', '-f', path, '--build-arg', 'ANSIBLE_GALAXY_CLI_ROLE_OPTS=--ignore-errors', '-c', str(tmp_path)])
    assert aee.build_args == {'ANSIBLE_GALAXY_CLI_ROLE_OPTS': '--ignore-errors'}


def test_build_context(good_exec_env_definition_path, tmp_path):
    path = str(good_exec_env_definition_path)
    build_context = str(tmp_path)

    aee = prepare(['build', '-f', path, '-c', build_context])
    assert aee.build_context == build_context


def test_build_no_cache(good_exec_env_definition_path, tmp_path):
    path = str(good_exec_env_definition_path)
    build_context = str(tmp_path)

    aee = prepare(['build', '-f', path, '-c', build_context])
    aee_no_cache = prepare(['build', '-f', path, '-c', build_context, '--no-cache'])

    assert '--no-cache' not in aee.build_command
    assert '--no-cache' in aee_no_cache.build_command


def test_build_multiple_tags(exec_env_definition_file, tmp_path):
    content = {'version': 1}
    path = str(exec_env_definition_file(content=content))

    # test with 'container' sub-command
    aee = prepare(['build', '--tag', 'TAG1', '--tag', 'TAG2', '-f', path, '-c', str(tmp_path)])
    assert aee.tags == ['TAG1', 'TAG2']


def test_default_tag(exec_env_definition_file, tmp_path):
    content = {'version': 1}
    path = str(exec_env_definition_file(content=content))

    # test with 'container' sub-command
    aee = prepare(['build', '-f', path, '-c', str(tmp_path)])
    assert aee.tags == [constants.default_tag]


def test_build_prune_images(good_exec_env_definition_path, tmp_path):
    path = str(good_exec_env_definition_path)
    build_context = str(tmp_path)

    aee_prune_images = prepare(['build', '-f', path, '-c', build_context, '--prune-images'])
    aee_no_prune_images = prepare(['build', '-f', path, '-c', build_context])

    assert aee_prune_images.prune_images
    assert 'prune' in aee_prune_images.prune_image_command
    assert not aee_no_prune_images.prune_images


def test_container_policy_default(exec_env_definition_file, tmp_path):
    '''
    Test default policy file behavior.

    Do not expect a policy file or forced pulls.
    '''
    content = {'version': 2}
    path = str(exec_env_definition_file(content=content))
    aee = prepare(['build', '-f', path, '-c', str(tmp_path)])
    assert aee.container_policy is None
    assert '--signature-policy=' not in aee.build_command
    assert '--pull-always' not in aee.build_command


def test_container_policy_signature_required(exec_env_definition_file, tmp_path):
    '''
    Test signature_required policy.

    Expect a policy file to be specified, and forced pulls.
    '''
    content = {'version': 2}
    path = str(exec_env_definition_file(content=content))

    keyring = tmp_path / 'keyring.gpg'
    keyring.touch()

    aee = prepare(['build',
                   '-f', path,
                   '-c', str(tmp_path),
                   '--container-policy', 'signature_required',
                   '--container-runtime', 'podman',
                   '--container-keyring', str(keyring),
                   ])
    assert aee.container_policy == PolicyChoices.SIG_REQ
    policy_path = os.path.join(str(tmp_path), constants.default_policy_file_name)
    assert f'--signature-policy={policy_path}' in aee.build_command
    assert '--pull-always' in aee.build_command


def test_container_policy_system(exec_env_definition_file, tmp_path):
    '''
    Test system policy.

    Do NOT expect a policy file, but do expect forced pulls.
    '''
    content = {'version': 2}
    path = str(exec_env_definition_file(content=content))
    aee = prepare(['build',
                   '-f', path,
                   '-c', str(tmp_path),
                   '--container-policy', 'system',
                   '--container-runtime', 'podman',
                   ])
    assert aee.container_policy == PolicyChoices.SYSTEM
    assert '--signature-policy=' not in aee.build_command
    assert '--pull-always' in aee.build_command


def test_container_policy_not_podman(exec_env_definition_file, tmp_path):
    '''Test --container-policy usage fails with non-podman runtime'''
    content = {'version': 2}
    path = str(exec_env_definition_file(content=content))

    with pytest.raises(ValueError, match='--container-policy is only valid with the podman runtime'):
        prepare(['build',
                 '-f', path,
                 '-c', str(tmp_path),
                 '--container-policy', 'signature_required',
                 '--container-runtime', 'docker',
                 '--container-keyring', 'TBD',
                 ])


def test_container_policy_missing_keyring(exec_env_definition_file, tmp_path):
    '''Test that a container policy that requires a keyring fails when it is missing.'''
    content = {'version': 2}
    path = str(exec_env_definition_file(content=content))
    with pytest.raises(ValueError, match='--container-policy=signature_required requires --container-keyring'):
        prepare(['build',
                 '-f', path,
                 '-c', str(tmp_path),
                 '--container-policy', 'signature_required',
                 '--container-runtime', 'podman',
                 ])


@pytest.mark.parametrize('policy', ('system', 'ignore_all'))
def test_container_policy_unnecessary_keyring(exec_env_definition_file, tmp_path, policy):
    '''Test that a container policy that doesn't require a keyring fails when it is supplied.'''
    content = {'version': 2}
    path = str(exec_env_definition_file(content=content))
    with pytest.raises(ValueError, match=f'--container-keyring is not valid with --container-policy={policy}'):
        prepare(['build',
                 '-f', path,
                 '-c', str(tmp_path),
                 '--container-policy', policy,
                 '--container-runtime', 'podman',
                 '--container-keyring', 'TBD',
                 ])


def test_container_policy_with_build_args_cli_opt(exec_env_definition_file, tmp_path):
    '''Test specifying image with --build-arg opt will fail'''
    content = {'version': 2}
    path = str(exec_env_definition_file(content=content))
    with pytest.raises(ValueError, match='EE_BASE_IMAGE not allowed in --build-arg option with version 2 format'):
        prepare(['build',
                 '-f', path,
                 '-c', str(tmp_path),
                 '--container-policy', 'signature_required',
                 '--container-runtime', 'podman',
                 '--container-keyring', 'TBD',
                 '--build-arg', 'EE_BASE_IMAGE=blah',
                 ])


def test_container_policy_with_version_1(exec_env_definition_file, tmp_path):
    '''Test --container-policy usage fails with version 1 EE format'''
    content = {'version': 1}
    path = str(exec_env_definition_file(content=content))

    with pytest.raises(ValueError, match='--container-policy not valid with version 1 format'):
        prepare(['build',
                 '-f', path,
                 '-c', str(tmp_path),
                 '--container-policy', 'signature_required',
                 '--container-runtime', 'podman',
                 '--container-keyring', 'TBD',
                 ])
