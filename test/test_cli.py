import pytest

from ansible_exec_env.cli import prepare
from ansible_exec_env.cli import run


def test_custom_image(exec_env_definition_file):
    content = {
        'version': 1
    }
    path = str(exec_env_definition_file(content=content))

    aee = prepare(['build', '-f', path, '-b', 'my-custom-image'])

    assert aee.containerfile.base_image == 'my-custom-image'


def test_build_context(good_exec_env_definition_path, tmpdir):
    path = str(good_exec_env_definition_path)
    build_context = str(tmpdir)
    aee = prepare(['build', '-f', path, '-c', build_context])

    assert aee.build_context == build_context
