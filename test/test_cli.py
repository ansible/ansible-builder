from ansible_builder.main import AnsibleBuilder
from ansible_builder.cli import parse_args


def prepare(args):
    args = parse_args(args)
    return AnsibleBuilder(**vars(args))


def test_custom_image(exec_env_definition_file, tmpdir):
    content = {'version': 1}
    path = str(exec_env_definition_file(content=content))

    aee = prepare(['build', '-f', path, '-b', 'my-custom-image', '-c', str(tmpdir)])

    assert aee.containerfile.base_image == 'my-custom-image'


def test_build_context(good_exec_env_definition_path, tmpdir):
    path = str(good_exec_env_definition_path)
    build_context = str(tmpdir)
    aee = prepare(['build', '-f', path, '-c', build_context])

    assert aee.build_context == build_context
