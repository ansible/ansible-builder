import yaml


def test_introspect_write(cli, data_dir):
    r = cli(f'ansible-builder introspect {data_dir}')
    data = yaml.safe_load(r.stdout)  # assure that output is valid YAML
    assert 'python' in data
    assert 'system' in data
    assert 'pytz  # from collection test.reqfile' in r.stdout


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
        'jinja2>=3.0  # from collection test.reqfile',
        'tacacs_plus  # from collection test.reqfile',
        'pyvcloud>=18.0.10  # from collection test.reqfile',
        '',
    ])


def test_introspect_with_user_reqs(cli, data_dir, tmp_path):
    user_file = tmp_path / 'requirements.txt'
    user_file.write_text("ansible\npytest\n")

    r = cli(f'ansible-builder introspect --user-pip={user_file} {data_dir}')
    data = yaml.safe_load(r.stdout)  # assure that output is valid YAML
    assert 'python' in data
    assert 'system' in data
    assert 'pytz  # from collection test.reqfile' in r.stdout
    # 'ansible' allowed in user requirements
    assert 'ansible  # from collection user' in r.stdout
    # 'pytest' allowed in user requirements
    assert 'pytest  # from collection user' in r.stdout


def test_introspect_exclude_python(cli, data_dir, tmp_path):
    exclude_file = tmp_path / 'exclude.txt'
    exclude_file.write_text("pytz\npython-dateutil\n")

    r = cli(f'ansible-builder introspect {data_dir} --exclude-pip-reqs={exclude_file}')
    data = yaml.safe_load(r.stdout)

    assert 'python' in data
    assert 'system' in data
    assert 'pytz' not in r.stdout
    assert 'python-dateutil' not in r.stdout


def test_introspect_exclude_system(cli, data_dir, tmp_path):
    exclude_file = tmp_path / 'exclude.txt'
    exclude_file.write_text("subversion\n")

    r = cli(f'ansible-builder introspect {data_dir} --exclude-bindep-reqs={exclude_file}')
    data = yaml.safe_load(r.stdout)

    assert 'python' in data
    assert 'system' in data
    assert 'subversion' not in r.stdout


def test_introspect_exclude_collections(cli, data_dir, tmp_path):
    exclude_file = tmp_path / 'exclude.txt'
    exclude_file.write_text("test.reqfile\ntest.bindep\n")

    r = cli(f'ansible-builder introspect {data_dir} --exclude-collection-reqs={exclude_file}')
    data = yaml.safe_load(r.stdout)

    assert 'python' in data
    assert 'system' in data
    assert 'from collection test.reqfile' not in r.stdout
    assert 'from collection test.bindep' not in r.stdout
