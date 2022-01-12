import re


def test_help(cli):
    result = cli('ansible-builder --help', check=False)
    help_text = result.stdout
    assert 'usage: ansible-builder [-h] [--version] {container} ...' in help_text


def test_no_args(cli):
    result = cli('ansible-builder', check=False)
    stderr = result.stderr
    assert 'usage: ansible-builder [-h] [--version] {container} ...' in stderr
    assert 'ansible-builder: error: the following arguments are required: command_type' in stderr


def test_version(cli):
    result = cli('ansible-builder --version')
    version = result.stdout
    matches = re.findall(r'\d.\d.\d', version)
    assert matches


def test_container_help(cli):
    result = cli('ansible-builder container --help', check=False)
    help_text = result.stdout
    assert 'usage: ansible-builder container [-h] CONTAINER_ACTION ...' in help_text
    assert re.search(r'create\s+Creates a build context', help_text)
    assert re.search(r'build\s+Builds a container image', help_text)
    assert re.search(r'introspect\s+Introspects collections in folder', help_text)


def test_container_build_help(cli):
    result = cli('ansible-builder container build --help', check=False)
    help_text = result.stdout
    assert 'usage: ansible-builder container build [-h]' in help_text
    assert re.search(r'Creates a build context', help_text)


def test_backward_compat_build_help(cli):
    result = cli('ansible-builder build --help', check=False)
    help_text = result.stdout
    assert 'usage: ansible-builder container build [-h]' in help_text
    assert re.search(r'Creates a build context', help_text)


def test_container_create_help(cli):
    result = cli('ansible-builder container create --help', check=False)
    help_text = result.stdout
    assert 'usage: ansible-builder container create [-h]' in help_text
    assert re.search(r'Creates a build context', help_text)


def test_backward_compat_create_help(cli):
    result = cli('ansible-builder create --help', check=False)
    help_text = result.stdout
    assert 'usage: ansible-builder container create [-h]' in help_text
    assert re.search(r'Creates a build context', help_text)


def test_container_introspect_help(cli):
    result = cli('ansible-builder container introspect --help', check=False)
    help_text = result.stdout
    assert 'usage: ansible-builder container introspect [-h] [--sanitize]' in help_text
    assert re.search(r'Loops over collections in folder', help_text)


def test_backward_compat_introspect_help(cli):
    result = cli('ansible-builder introspect --help', check=False)
    help_text = result.stdout
    assert 'usage: ansible-builder container introspect [-h] [--sanitize]' in help_text
    assert re.search(r'Loops over collections in folder', help_text)
