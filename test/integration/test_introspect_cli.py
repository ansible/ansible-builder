import yaml


def test_introspect_write(cli, data_dir):
    r = cli(f'ansible-builder introspect {data_dir}')
    print(r.stdout)
    data = yaml.safe_load(r.stdout)  # assure that output is valid YAML
    assert 'python' in data
    assert 'system' in data
    assert 'pytz' in data['python']['test.reqfile']


def test_introspect_with_sanitize(cli, data_dir):
    r = cli(f'ansible-builder introspect --sanitize {data_dir}')
    print(r.stdout)
    data = yaml.safe_load(r.stdout)  # assure that output is valid YAML
    assert 'python' in data
    assert 'system' in data
    assert '# from collection test.bindep' in r.stdout  # should have comments
