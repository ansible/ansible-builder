import re


def test_help(cli):
    result = cli('ansible-builder --help', check=False)
    help_text = result.stdout
    assert 'usage: ansible-builder [-h] [--version] {create,build,introspect} ...' in help_text


def test_no_args(cli):
    result = cli('ansible-builder', check=False)
    stderr = result.stderr
    assert 'usage: ansible-builder [-h] [--version] {create,build,introspect} ...' in stderr
    assert 'ansible-builder: error: the following arguments are required: action' in stderr


def test_version(cli):
    result = cli('ansible-builder --version')
    version = result.stdout
    matches = re.findall(r'\d.\d.\d', version)
    assert matches


def test_build_help(cli):
    result = cli('ansible-builder build --help', check=False)
    help_text = result.stdout
    assert 'usage: ansible-builder build [-h]' in help_text
    assert re.search(r'Creates a build context', help_text)


def test_create_help(cli):
    result = cli('ansible-builder create --help', check=False)
    help_text = result.stdout
    assert 'usage: ansible-builder create [-h]' in help_text
    assert re.search(r'Creates a build context', help_text)


def test_introspect_help(cli):
    result = cli('ansible-builder introspect --help', check=False)
    help_text = result.stdout
    assert 'usage: ansible-builder introspect [-h] [--sanitize]' in help_text
    assert re.search(r'Loops over collections in folder', help_text)
