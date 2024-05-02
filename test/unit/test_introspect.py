import os
import pytest

from ansible_builder._target_scripts.introspect import (parse_args,
                                                        process,
                                                        process_collection,
                                                        filter_requirements,
                                                        strip_comments)


def test_multiple_collection_metadata(data_dir):
    files = process(data_dir)
    files['python'] = filter_requirements(files['python'])
    files['system'] = filter_requirements(files['system'], is_python=False)

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


def test_process_returns_excluded_python(data_dir, tmp_path):
    """
    Test that process() return value is properly formatted for excluded Python reqs.
    """
    pip_ignore_file = tmp_path / "exclude-requirements.txt"
    pip_ignore_file.write_text("req1\nreq2")

    retval = process(data_dir, exclude_pip=str(pip_ignore_file))

    assert 'python' in retval
    assert 'exclude' in retval['python']
    assert retval['python']['exclude'] == ['req1', 'req2']


def test_process_returns_excluded_system(data_dir, tmp_path):
    """
    Test that process() return value is properly formatted for excluded system reqs.
    """
    bindep_ignore_file = tmp_path / "exclude-bindep.txt"
    bindep_ignore_file.write_text("req1\nreq2")

    retval = process(data_dir, exclude_bindep=str(bindep_ignore_file))

    assert 'system' in retval
    assert 'exclude' in retval['system']
    assert retval['system']['exclude'] == ['req1', 'req2']


def test_process_returns_excluded_collections(data_dir, tmp_path):
    """
    Test that process() return value is properly formatted for excluded collections.
    """
    col_ignore_file = tmp_path / "ignored_collections"
    col_ignore_file.write_text("a.b\nc.d")

    retval = process(data_dir, exclude_collections=str(col_ignore_file))

    assert 'excluded_collections' in retval
    assert retval['excluded_collections'] == ['a.b', 'c.d']


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


def test_filter_requirements_pep508():
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

    assert filter_requirements(reqs) == expected


def test_comment_parsing():
    """
    Test that filter_requirements() does not remove embedded URL anchors due to comment parsing.
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

    assert filter_requirements(reqs) == expected


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
    Test that filter_requirements() will pass through non-pep508 data.
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

    assert filter_requirements(reqs) == expected


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

    assert filter_requirements(reqs, exclude=excluded, is_python=False) == expected


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

    assert filter_requirements(reqs, excluded) == expected


def test_filter_requirements_excludes_collections():
    """
    Test that excluding all requirements from a list of collections works in filter_requirements().
    """
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
        "e.f": [
            "req5",
        ],
        "user": [
            "req1"   # should never exclude from user reqs
        ]
    }

    excluded_collections = [
        'a.b',
        'e.f',
    ]

    expected = [
        "req1<=2.0.0  # from collection c.d",
        "req3  # from collection c.d",
        "req1  # from collection user",
    ]

    assert filter_requirements(reqs, exclude_collections=excluded_collections) == expected


def test_requirement_regex_exclusions():
    reqs = {
        "a.b": [
            "foo",
            "shimmy",
            "kungfoo",
            "aaab",
        ],
        "c.d": [
            "foobar",
            "shake",
            "ab",
        ]
    }

    excluded = [
        "Foo",       # straight string comparison (case shouldn't matter)
        "foo.",      # straight string comparison (shouldn't match)
        "~foo.",     # regex (shouldn't match b/c not full string match)
        "~Sh.*",     # regex (case shouldn't matter)
        "~^.+ab",    # regex
    ]

    expected = [
        "kungfoo  # from collection a.b",
        "foobar  # from collection c.d",
        "ab  # from collection c.d"
    ]

    assert filter_requirements(reqs, excluded) == expected


def test_collection_regex_exclusions():
    reqs = {
        "a.b": ["foo"],
        "c.d": ["bar"],
        "ab.cd": ["foobar"],
        "e.f": ["baz"],
        "be.fun": ["foobaz"],
    }

    excluded_collections = [
        r"~A\..+",     # regex (case shouldn't matter)
        "E.F",         # straight string comparison (case shouldn't matter)
        "~b.c",        # regex (shouldn't match b/c not full string match)
    ]

    expected = [
        "bar  # from collection c.d",
        "foobar  # from collection ab.cd",
        "foobaz  # from collection be.fun",
    ]

    assert filter_requirements(reqs, exclude_collections=excluded_collections) == expected
