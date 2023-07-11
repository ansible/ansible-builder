import os
import pytest

from ansible_builder._target_scripts.introspect import process, process_collection, simple_combine, sanitize_requirements
from ansible_builder._target_scripts.introspect import parse_args


def test_multiple_collection_metadata(data_dir):

    files = process(data_dir)
    files['python'] = sanitize_requirements(files['python'])
    files['system'] = simple_combine(files['system'])

    assert files == {'python': [
        'pyvcloud>=14,>=18.0.10  # from collection test.metadata,test.reqfile',
        'pytz  # from collection test.reqfile',
        # python-dateutil should appear only once even though referenced in
        # multiple places, once with a dash and another with an underscore in the name.
        'python_dateutil>=2.8.2  # from collection test.reqfile',
        # jinja2 should appear only once even though referenced in multiple
        # places, once with uppercase and another with lowercase in the name.
        'jinja2>=3.0  # from collection test.reqfile',
        'tacacs_plus  # from collection test.reqfile'
    ], 'system': [
        'subversion [platform:rpm]  # from collection test.bindep',
        'subversion [platform:dpkg]  # from collection test.bindep'
    ]}


def test_single_collection_metadata(data_dir):

    col_path = os.path.join(data_dir, 'ansible_collections', 'test', 'metadata')
    py_reqs, sys_reqs = process_collection(col_path)

    assert py_reqs == ['pyvcloud>=14']
    assert sys_reqs == []


def test_parse_args_empty(capsys):
    with pytest.raises(SystemExit):
        parse_args()
    dummy, err = capsys.readouterr()
    assert 'usage: introspect' in err


def test_parse_args_default_action():
    action = 'introspect'
    user_pip = '/tmp/user-pip.txt'
    user_bindep = '/tmp/user-bindep.txt'
    write_pip = '/tmp/write-pip.txt'
    write_bindep = '/tmp/write-bindep.txt'

    parser = parse_args(
        [
            action, '--sanitize',
            f'--user-pip={user_pip}',
            f'--user-bindep={user_bindep}',
            f'--write-pip={write_pip}',
            f'--write-bindep={write_bindep}',
        ]
    )

    assert parser.action == action
    assert parser.sanitize
    assert parser.user_pip == user_pip
    assert parser.user_bindep == user_bindep
    assert parser.write_pip == write_pip
    assert parser.write_bindep == write_bindep
