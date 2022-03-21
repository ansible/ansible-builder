import yaml


def test_introspect_write(cli, data_dir):
    r = cli(f'ansible-builder introspect {data_dir}')
    data = yaml.safe_load(r.stdout)  # assure that output is valid YAML
    assert 'python' in data
    assert 'system' in data
    assert 'pytz' in data['python']['test.reqfile']


def test_introspect_with_sanitize(cli, data_dir):
    r = cli(f'ansible-builder introspect --sanitize {data_dir}')
    data = yaml.safe_load(r.stdout)  # assure that output is valid YAML
    assert 'python' in data
    assert 'system' in data
    assert '# from collection test.bindep' in r.stdout  # should have comments


def test_introspect_write_bindep(cli, data_dir, tmp_path):
    dest_file = tmp_path / 'req.txt'
    cli(f'ansible-builder introspect {data_dir} --write-bindep={dest_file}')

    assert dest_file.read_text() == '\n'.join([
        'subversion [platform:rpm]  # from collection test.bindep',
        'subversion [platform:dpkg]  # from collection test.bindep',
        '',
    ])


def test_introspect_write_python(cli, data_dir, tmp_path):
    dest_file = tmp_path / 'req.txt'
    cli(f'ansible-builder introspect {data_dir} --write-pip={dest_file}')

    assert dest_file.read_text() == '\n'.join([
        'pyvcloud>=14  # from collection test.metadata',
        'pytz  # from collection test.reqfile',
        'python-dateutil>=2.8.2  # from collection test.reqfile',
        'tacacs_plus  # from collection test.reqfile',
        'pyvcloud>=18.0.10  # from collection test.reqfile',
        '',
    ])


def test_introspect_write_python_and_sanitize(cli, data_dir, tmp_path):
    dest_file = tmp_path / 'req.txt'
    cli(f'ansible-builder introspect {data_dir} --write-pip={dest_file} --sanitize')

    assert dest_file.read_text() == '\n'.join([
        'pyvcloud>=14,>=18.0.10  # from collection test.metadata,test.reqfile',
        'pytz  # from collection test.reqfile',
        'python-dateutil>=2.8.2  # from collection test.reqfile',
        'tacacs-plus  # from collection test.reqfile',
        '',
    ])


def test_introspect_with_sanitize_user_reqs(cli, data_dir, tmp_path):
    user_file = tmp_path / 'requirements.txt'
    user_file.write_text("ansible\npytest\n")

    r = cli(f'ansible-builder introspect --sanitize --user-pip={user_file} {data_dir}')
    data = yaml.safe_load(r.stdout)  # assure that output is valid YAML
    assert 'python' in data
    assert 'system' in data
    assert 'pytz  # from collection test.reqfile' in data['python']

    # 'ansible' allowed in user requirements
    assert 'ansible  # from collection user' in data['python']
    # 'pytest' allowed in user requirements
    assert 'pytest  # from collection user' in data['python']
