import os
import runpy
import shlex

import pytest

from ansible_builder import constants
from ansible_builder.main import AnsibleBuilder
from ansible_builder.cli import parse_args, _should_disable_colors
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

    aee = prepare(
        [
            'build', '-f', path, '--build-arg',
            'ANSIBLE_GALAXY_CLI_ROLE_OPTS=--ignore-errors', '-c', str(tmp_path)
        ]
    )
    assert aee.build_args == {'ANSIBLE_GALAXY_CLI_ROLE_OPTS': '--ignore-errors'}


def test_build_args_empty_value(exec_env_definition_file, tmp_path):
    content = {'version': 3, 'images': {'base_image': {'name': 'base_image:latest'}}}
    path = str(exec_env_definition_file(content=content))

    aee = prepare(['build', '-f', path, '--build-arg', 'ANSIBLE_GALAXY_CLI_ROLE_OPTS=', '-c', str(tmp_path)])
    assert aee.build_args == {'ANSIBLE_GALAXY_CLI_ROLE_OPTS': ''}


def test_build_args_no_trailing_equal(exec_env_definition_file, tmp_path):
    content = {'version': 3, 'images': {'base_image': {'name': 'base_image:latest'}}}
    path = str(exec_env_definition_file(content=content))

    aee = prepare(['build', '-f', path, '--build-arg', 'ANSIBLE_GALAXY_CLI_ROLE_OPTS', '-c', str(tmp_path)])
    assert aee.build_args == {'ANSIBLE_GALAXY_CLI_ROLE_OPTS': None}


def test_build_args_multiple_equal_sign_value(exec_env_definition_file, tmp_path):
    content = {'version': 3, 'images': {'base_image': {'name': 'base_image:latest'}}}
    path = str(exec_env_definition_file(content=content))

    aee = prepare(['build', '-f', path,
                   '--build-arg', 'ANSIBLE_GALAXY_CLI_ROLE_OPTS=',
                   '--build-arg', 'PYTHON_CONFIG_SETTINGS=--config-setting=--global-option=--tag-build=SUFFIX',
                   '-c', str(tmp_path)])
    assert aee.build_args == {
        'PYTHON_CONFIG_SETTINGS': '--config-setting=--global-option=--tag-build=SUFFIX',
        'ANSIBLE_GALAXY_CLI_ROLE_OPTS': ''
    }


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


@pytest.mark.parametrize('version', (2, 3))
def test_container_policy_default(exec_env_definition_file, tmp_path, version):
    '''
    Test default policy file behavior.

    Do not expect a policy file or forced pulls.
    '''
    content = {'version': version}
    path = str(exec_env_definition_file(content=content))
    aee = prepare(['build', '-f', path, '-c', str(tmp_path)])
    assert aee.container_policy is None
    assert '--signature-policy=' not in aee.build_command
    assert '--pull-always' not in aee.build_command


@pytest.mark.parametrize('version', (2, 3))
def test_container_policy_signature_required(exec_env_definition_file, tmp_path, version):
    '''
    Test signature_required policy.

    Expect a policy file to be specified, and forced pulls.
    '''
    content = {'version': version}
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


@pytest.mark.parametrize('version', (2, 3))
def test_container_policy_system(exec_env_definition_file, tmp_path, version):
    '''
    Test system policy.

    Do NOT expect a policy file, but do expect forced pulls.
    '''
    content = {'version': version}
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


@pytest.mark.parametrize('version', (2, 3))
def test_container_policy_not_podman(exec_env_definition_file, tmp_path, version):
    '''Test --container-policy usage fails with non-podman runtime'''
    content = {'version': version}
    path = str(exec_env_definition_file(content=content))

    with pytest.raises(ValueError, match='--container-policy is only valid with the podman runtime'):
        prepare(['build',
                 '-f', path,
                 '-c', str(tmp_path),
                 '--container-policy', 'signature_required',
                 '--container-runtime', 'docker',
                 '--container-keyring', 'TBD',
                 ])


@pytest.mark.parametrize('version', (2, 3))
def test_container_policy_missing_keyring(exec_env_definition_file, tmp_path, version):
    '''Test that a container policy that requires a keyring fails when it is missing.'''
    content = {'version': version}
    path = str(exec_env_definition_file(content=content))
    with pytest.raises(ValueError, match='--container-policy=signature_required requires --container-keyring'):
        prepare(['build',
                 '-f', path,
                 '-c', str(tmp_path),
                 '--container-policy', 'signature_required',
                 '--container-runtime', 'podman',
                 ])


@pytest.mark.parametrize('policy', ('system', 'ignore_all'))
@pytest.mark.parametrize('version', (2, 3))
def test_container_policy_unnecessary_keyring(exec_env_definition_file, tmp_path, policy, version):
    '''Test that a container policy that doesn't require a keyring fails when it is supplied.'''
    content = {'version': version}
    path = str(exec_env_definition_file(content=content))
    with pytest.raises(ValueError, match=f'--container-keyring is not valid with --container-policy={policy}'):
        prepare(['build',
                 '-f', path,
                 '-c', str(tmp_path),
                 '--container-policy', policy,
                 '--container-runtime', 'podman',
                 '--container-keyring', 'TBD',
                 ])


@pytest.mark.parametrize('version', (2, 3))
def test_container_policy_with_build_args_cli_opt(exec_env_definition_file, tmp_path, version):
    '''Test specifying image with --build-arg opt will fail'''
    content = {'version': version}
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


def test_squash_default(exec_env_definition_file, tmp_path):
    '''
    Test the squash CLI option with default.
    '''
    content = {'version': 3, 'images': {'base_image': {'name': 'base_image:latest'}}}
    path = str(exec_env_definition_file(content=content))
    aee = prepare(['build',
                   '-f', path,
                   '-c', str(tmp_path),
                   '--container-runtime', 'podman',
                   ])
    assert '--squash' not in aee.build_command


def test_squash_all(exec_env_definition_file, tmp_path):
    '''
    Test the squash CLI option with 'all'.
    '''
    content = {'version': 3, 'images': {'base_image': {'name': 'base_image:latest'}}}
    path = str(exec_env_definition_file(content=content))
    aee = prepare(['build',
                   '-f', path,
                   '-c', str(tmp_path),
                   '--container-runtime', 'podman',
                   '--squash', 'all'
                   ])
    assert '--squash-all' in aee.build_command


def test_squash_off(exec_env_definition_file, tmp_path):
    '''
    Test the squash CLI option with 'off'.
    '''
    content = {'version': 3, 'images': {'base_image': {'name': 'base_image:latest'}}}
    path = str(exec_env_definition_file(content=content))
    aee = prepare(['build',
                   '-f', path,
                   '-c', str(tmp_path),
                   '--container-runtime', 'podman',
                   '--squash', 'off'
                   ])
    assert '--squash' not in aee.build_command


def test_squash_new(exec_env_definition_file, tmp_path):
    '''
    Test the squash CLI option with 'new'.
    '''
    content = {'version': 3, 'images': {'base_image': {'name': 'base_image:latest'}}}
    path = str(exec_env_definition_file(content=content))
    aee = prepare(['build',
                   '-f', path,
                   '-c', str(tmp_path),
                   '--container-runtime', 'podman',
                   '--squash', 'new'
                   ])
    assert '--squash' in aee.build_command
    assert '--squash-all' not in aee.build_command


def test_squash_ignored(exec_env_definition_file, tmp_path):
    '''
    Test the squash CLI option is ignored with docker.
    '''
    content = {'version': 3, 'images': {'base_image': {'name': 'base_image:latest'}}}
    path = str(exec_env_definition_file(content=content))
    aee = prepare(['build',
                   '-f', path,
                   '-c', str(tmp_path),
                   '--container-runtime', 'docker',
                   '--squash', 'all'
                   ])
    assert '--squash' not in aee.build_command


def test_as_executable_module(capsys):
    """
    Test __main__ shim as if invoked by `python -m ansible_builder`
    """
    with pytest.raises(SystemExit) as sysexit:
        runpy.run_module('ansible_builder', run_name='__main__', alter_sys=True)

    assert sysexit.value.code == 2  # default rc for "usage"
    captured = capsys.readouterr()
    assert "usage" in captured.err


@pytest.mark.parametrize('verbosity_opt,expected_val',
                         [('-v', 1),
                          ('-v -v', 2),
                          ('-vvv', 3),
                          ('-v 1', 1),
                          ('--verbosity', 1),
                          ('--verbosity=2', 2)])
def test_verbosity(exec_env_definition_file, tmp_path, verbosity_opt, expected_val):
    content = {'version': 3, 'images': {'base_image': {'name': 'base_image:latest'}}}
    path = str(exec_env_definition_file(content=content))

    aee = prepare(['create',
                   '-f', path,
                   '-c', str(tmp_path),
                   verbosity_opt,
                   ])
    assert aee.verbosity == expected_val


@pytest.mark.parametrize('verbosity_opt', ['-v4', '-vvvv', '-v -v -v -v', '--verbosity=4'])
def test_invalid_verbosity(exec_env_definition_file, tmp_path, verbosity_opt):
    content = {'version': 3, 'images': {'base_image': {'name': 'base_image:latest'}}}
    path = str(exec_env_definition_file(content=content))
    with pytest.raises(ValueError, match=f'maximum verbosity is {constants.max_verbosity}'):
        prepare(['create', '-f', path, '-c', str(tmp_path), verbosity_opt])


def test_extra_build_cli_args(exec_env_definition_file, tmp_path):
    content = {'version': 3, 'images': {'base_image': {'name': 'base_image:latest'}}}
    path = str(exec_env_definition_file(content=content))
    extras = ['--cache-ttl', '--mount=type=secret,id=mytoken', '--compress', '--env=TEST="blah blah"']

    aee = prepare(['build',
                   '-f', path,
                   '-c', str(tmp_path),
                   '--extra-build-cli-args', shlex.join(extras),
                   ])

    for extra in extras:
        assert extra in aee.build_command


@pytest.mark.parametrize('no_color,clicolor,term,ci,expected',
                         [
                             # NO_COLOR standard
                             ('1', '', 'xterm', '', True),     # NO_COLOR disables
                             ('1', '1', 'xterm', '', True),    # NO_COLOR overrides CLICOLOR

                             # TERM=dumb
                             ('', '', 'dumb', '', True),       # TERM=dumb disables

                             # CLICOLOR
                             ('', '0', 'xterm', '', True),     # CLICOLOR=0 disables
                             ('', '1', 'xterm', '', False),    # CLICOLOR=1 enables
                             ('', '', 'xterm', '', False),     # Default CLICOLOR behavior (enabled)

                             # CI environments
                             ('', '', 'xterm', '1', True),     # CI disables colors
                         ])
def test__should_disable_colors(no_color, clicolor, term, ci, expected, monkeypatch, mocker):
    # pylint: disable=W0613,W0621
    # Clear environment variables that could interfere with the test
    # monkeypatch.delenv is safe for concurrent execution
    for var in ['NO_COLOR', 'CLICOLOR', 'TERM',
                'CI', 'CONTINUOUS_INTEGRATION', 'BUILD_NUMBER', 'GITHUB_ACTIONS']:
        monkeypatch.delenv(var, raising=False)

    # Set test values using monkeypatch (thread-safe)
    if no_color:
        monkeypatch.setenv('NO_COLOR', no_color)
    if clicolor:
        monkeypatch.setenv('CLICOLOR', clicolor)
    if term:
        monkeypatch.setenv('TERM', term)
    if ci:
        monkeypatch.setenv('CI', ci)

    # Mock TTY detection to return True (simulating terminal environment)
    # This prevents test environment from interfering with color detection logic
    mocker.patch('sys.stdout.isatty', return_value=True)
    assert _should_disable_colors() == expected


@pytest.mark.parametrize('isatty_result,expected', [
    (True, False),   # TTY - colors enabled
    (False, True),   # Not TTY - colors disabled
])
def test__should_disable_colors_tty_detection(isatty_result, expected, monkeypatch, mocker):
    # pylint: disable=W0613,W0621
    # Clear all color-related environment variables using monkeypatch
    for var in ['NO_COLOR', 'CLICOLOR', 'TERM',
                'CI', 'CONTINUOUS_INTEGRATION', 'BUILD_NUMBER', 'GITHUB_ACTIONS']:
        monkeypatch.delenv(var, raising=False)

    # Mock sys.stdout.isatty to control TTY detection
    mocker.patch('sys.stdout.isatty', return_value=isatty_result)
    assert _should_disable_colors() == expected
