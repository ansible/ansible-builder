import os


def test_introspect_write(cli, data_dir, tmpdir):
    dest_file = os.path.join(str(tmpdir), 'req.txt')
    cli(f'ansible-builder introspect {data_dir} --write-bindep={dest_file}')
    with open(dest_file, 'r') as f:
        assert f.read() == '\n'.join([
            'subversion [platform:rpm]  # from collection test.bindep',
            'subversion [platform:dpkg]  # from collection test.bindep',
            ''
        ])
