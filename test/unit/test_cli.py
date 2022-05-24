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
    content = {'version': 1}
    path = str(exec_env_definition_file(content=content))
    aee = prepare(['build', '-f', path, '-c', str(tmp_path)])
    assert aee.container_policy == PolicyChoices.SYSTEM


def test_container_policy(exec_env_definition_file, tmp_path):
    content = {'version': 1}
    path = str(exec_env_definition_file(content=content))
    aee = prepare(['build', '-f', path, '-c', str(tmp_path), '--container-policy', 'signature_required'])
    assert aee.container_policy == PolicyChoices.SIG_REQ
