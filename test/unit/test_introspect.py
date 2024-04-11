import os
import pytest

from ansible_builder._target_scripts.introspect import (parse_args,
                                                        process,
                                                        process_collection,
                                                        simple_combine,
                                                        strip_comments)


def test_multiple_collection_metadata(data_dir):

    files = process(data_dir)
    files['python'] = simple_combine(files['python'])
    files['system'] = simple_combine(files['system'], is_python=False)

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


def test_comment_parsing():
    """
    Test that simple_combine() does not remove embedded URL anchors due to comment parsing.
    """
    reqs = {
        'a.b': [
            '# comment 1',
            'git+https://git.repo/some_pkg.git#egg=SomePackage',
            'git+https://git.repo/some_pkg.git#egg=SomeOtherPackage  # inline comment',
            'git+https://git.repo/some_pkg.git#egg=AlsoSomePackage #inline comment that hates leading spaces',
            '    # crazy indented comment (waka waka!)',
            '####### something informative'
            '    ',
            '',
        ]
    }

    expected = [
        'git+https://git.repo/some_pkg.git#egg=SomePackage',
        'git+https://git.repo/some_pkg.git#egg=SomeOtherPackage',
        'git+https://git.repo/some_pkg.git#egg=AlsoSomePackage',
    ]

    assert simple_combine(reqs) == expected


def test_strip_comments():
    """
    Test that strip_comments() properly removes comments from Python requirements input.
    """
    reqs = {
        'a.b': [
            '# comment 1',
            'git+https://git.repo/some_pkg.git#egg=SomePackage',
            'git+https://git.repo/some_pkg.git#egg=SomeOtherPackage  # inline comment',
            'git+https://git.repo/some_pkg.git#egg=AlsoSomePackage #inline comment that hates leading spaces',
            '    # crazy indented comment (waka waka!)',
            '####### something informative'
            '    ',
            '',
        ],
        'c.d': [
            '# comment 2',
            'git',
        ]
    }

    expected = {
        'a.b': [
            'git+https://git.repo/some_pkg.git#egg=SomePackage',
            'git+https://git.repo/some_pkg.git#egg=SomeOtherPackage',
            'git+https://git.repo/some_pkg.git#egg=AlsoSomePackage',
        ],
        'c.d': [
            'git',
        ]
    }

    assert strip_comments(reqs) == expected


def test_python_pass_thru():
    """
    Test that simple_combine() will pass through non-pep508 data.
    """
    reqs = {
        # various VCS and URL options
        'a.b': [
            'git+https://git.repo/some_pkg.git#egg=SomePackage',
            'svn+svn://svn.repo/some_pkg/trunk/#egg=SomePackage',
            'https://example.com/foo/foo-0.26.0-py2.py3-none-any.whl',
            'http://my.package.repo/SomePackage-1.0.4.zip',
        ],

        # various 'pip install' options
        'c.d': [
            '-i https://pypi.org/simple',
            '--extra-index-url http://my.package.repo/simple',
            '--no-clean',
            '-e svn+http://svn.example.com/svn/MyProject/trunk@2019#egg=MyProject',
        ]
    }

    expected = [
        'git+https://git.repo/some_pkg.git#egg=SomePackage',
        'svn+svn://svn.repo/some_pkg/trunk/#egg=SomePackage',
        'https://example.com/foo/foo-0.26.0-py2.py3-none-any.whl',
        'http://my.package.repo/SomePackage-1.0.4.zip',
        '-i https://pypi.org/simple',
        '--extra-index-url http://my.package.repo/simple',
        '--no-clean',
        '-e svn+http://svn.example.com/svn/MyProject/trunk@2019#egg=MyProject',
    ]

    assert simple_combine(reqs) == expected


def test_excluded_system_requirements():
    reqs = {
        'a.b': [
            'libxml2-dev [platform:dpkg]',
            'dev-libs/libxml2',
            'python3-lxml [(platform:redhat platform:base-py3)]',
            'foo [platform:bar]',
        ],
        'c.d': [
            '# python is in EXCLUDED_REQUIREMENTS',
            'python [platform:brew] ==3.7.3',
            'libxml2-dev [platform:dpkg]',
            'python3-all-dev [platform:dpkg !platform:ubuntu-precise]',
        ],
        'user': [
            'foo',   # should never exclude from user reqs
        ]
    }

    excluded = ['python3-lxml', 'foo']

    expected = [
        'libxml2-dev [platform:dpkg]  # from collection a.b',
        'dev-libs/libxml2  # from collection a.b',
        'libxml2-dev [platform:dpkg]  # from collection c.d',
        'python3-all-dev [platform:dpkg !platform:ubuntu-precise]  # from collection c.d',
        'foo  # from collection user',
    ]

    assert simple_combine(reqs, exclude=excluded, is_python=False) == expected


def test_excluded_python_requirements():
    reqs = {
        "a.b": [
            "req1",
            "req2==0.1.0",
            "req4 ; python_version<='3.9'",
            "git+https://git.repo/some_pkg.git#egg=SomePackage",
        ],
        "c.d": [
            "req1<=2.0.0",
            "req3",
        ],
        "user": [
            "req1"   # should never exclude from user reqs
        ]
    }

    excluded = [
        "req1",
        "req4",
        "git",
    ]

    expected = [
        "req2==0.1.0  # from collection a.b",
        "git+https://git.repo/some_pkg.git#egg=SomePackage",
        "req3  # from collection c.d",
        "req1  # from collection user",
    ]

    assert simple_combine(reqs, excluded) == expected
