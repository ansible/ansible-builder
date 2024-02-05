import os
import pytest

from ansible_builder._target_scripts.introspect import process, process_collection
from ansible_builder._target_scripts.introspect import simple_combine
from ansible_builder._target_scripts.introspect import parse_args


def test_multiple_collection_metadata(data_dir):

    files = process(data_dir)
    files['python'] = simple_combine(files['python'])
    files['system'] = simple_combine(files['system'])

    assert files == {'python': [
        'pyvcloud>=14  # from collection test.metadata',
        'pytz  # from collection test.reqfile',
        'python-dateutil>=2.8.2  # from collection test.reqfile',
        'jinja2>=3.0  # from collection test.reqfile',
        'tacacs_plus  # from collection test.reqfile',
        'pyvcloud>=18.0.10  # from collection test.reqfile'
    ], 'system': [
        'subversion [platform:rpm]  # from collection test.bindep',
        'subversion [platform:dpkg]  # from collection test.bindep'
    ]}


def test_single_collection_metadata(data_dir):

    col_path = os.path.join(data_dir, 'ansible_collections', 'test', 'metadata')
    py_reqs, sys_reqs = process_collection(col_path)

    assert py_reqs == ['pyvcloud>=14']
    assert not sys_reqs


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
            action,
            f'--user-pip={user_pip}',
            f'--user-bindep={user_bindep}',
            f'--write-pip={write_pip}',
            f'--write-bindep={write_bindep}',
        ]
    )

    assert parser.action == action
    assert parser.user_pip == user_pip
    assert parser.user_bindep == user_bindep
    assert parser.write_pip == write_pip
    assert parser.write_bindep == write_bindep


def test_yaml_extension(data_dir):
    """
    Test that introspection recognizes a collection meta directory EE with a .yaml file extension.

    NOTE: This test depends on the meta EE in the collection to reference a file other than "requirements.txt"
    because of the way CollectionDefinition.__init__() will fall through to a default if the meta EE is not
    found.
    """
    col_path = os.path.join(data_dir, 'alternate_collections')
    files = process(col_path)
    assert files == {
        'python': {'test_collection.test_yaml_extension': ['python-six']},
        'system': {},
    }


def test_sanitize_pep508():
    reqs = {
        'a.b': [
            'foo[ext1,ext3] == 1',
            'bar; python_version < "2.7"',
            'A',
            "name",
        ],
        'c.d': [
            'FOO >= 1',
            'bar; python_version < "3.6"',
            "name<=1",
        ],
        'e.f': [
            'foo[ext2] @ git+http://github.com/foo/foo.git',
            "name>=3",
        ],
        'g.h': [
            "name>=3,<2",
        ],
        'i.j': [
            "name@http://foo.com",
        ],
        'k.l': [
            "name [fred,bar] @ http://foo.com ; python_version=='2.7'",
        ],
        'm.n': [
            "name[quux, strange];python_version<'2.7' and platform_version=='2'",
        ],
    }

    expected = [
        'foo[ext1,ext3] == 1  # from collection a.b',
        'bar; python_version < "2.7"  # from collection a.b',
        'A  # from collection a.b',
        'name  # from collection a.b',
        'FOO >= 1  # from collection c.d',
        'bar; python_version < "3.6"  # from collection c.d',
        'name<=1  # from collection c.d',
        'foo[ext2] @ git+http://github.com/foo/foo.git  # from collection e.f',
        'name>=3  # from collection e.f',
        'name>=3,<2  # from collection g.h',
        'name@http://foo.com  # from collection i.j',
        "name [fred,bar] @ http://foo.com ; python_version=='2.7'  # from collection k.l",
        "name[quux, strange];python_version<'2.7' and platform_version=='2'  # from collection m.n"
    ]

    assert simple_combine(reqs) == expected
