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
    pip_out = tmp_path / 'pip-output.txt'

    cli(f'ansible-builder introspect --user-pip={user_file} --write-pip={pip_out} {data_dir}')

    pip_data = pip_out.read_text()
    assert 'pytz  # from collection test.reqfile' in pip_data
    # 'ansible' allowed in user requirements
    assert 'ansible  # from collection user' in pip_data
    # 'pytest' allowed in user requirements
    assert 'pytest  # from collection user' in pip_data


def test_introspect_exclude_python(cli, data_dir, tmp_path):
    exclude_file = tmp_path / 'exclude.txt'
    exclude_file.write_text("pytz\npython-dateutil\n")
    pip_out = tmp_path / 'pip-output.txt'

    cli(f'ansible-builder introspect {data_dir} --exclude-pip-reqs={exclude_file} --write-pip={pip_out}')

    pip_data = pip_out.read_text()
    assert 'pytz' not in pip_data
    assert 'python-dateutil' not in pip_data


def test_introspect_exclude_system(cli, data_dir, tmp_path):
    exclude_file = tmp_path / 'exclude.txt'
    exclude_file.write_text("subversion\n")
    sys_out = tmp_path / 'sys-output.txt'

    cli(f'ansible-builder introspect {data_dir} --exclude-bindep-reqs={exclude_file} --write-bindep={sys_out}')

    # Everything was excluded, so there should be no output file.
    assert not sys_out.exists()


def test_introspect_exclude_collections(cli, data_dir, tmp_path):
    exclude_file = tmp_path / 'exclude.txt'
    exclude_file.write_text("test.reqfile\ntest.bindep\n")
    pip_out = tmp_path / 'pip-output.txt'

    cli(f'ansible-builder introspect {data_dir} --exclude-collection-reqs={exclude_file} --write-pip={pip_out}')

    pip_data = pip_out.read_text()
    assert 'from collection test.reqfile' not in pip_data
    assert 'from collection test.bindep' not in pip_data
