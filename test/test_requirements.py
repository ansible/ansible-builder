import pytest

from ansible_builder.requirements import (
    sanitize_python_requirements,
    sanitize_system_requirements,
    parse_bindep_lines,
    render_bindep_data
)


def test_combine_entries():
    assert sanitize_python_requirements({
        'foo.bar': ['foo>1.0'],
        'bar.foo': ['foo>=2.0']
    }) == ['foo>1.0,>=2.0  # from collection foo.bar,bar.foo']


def test_remove_unwanted_requirements():
    assert sanitize_python_requirements({
        'foo.bar': [
            'foo',
            'ansible',
            'bar',
        ],
        'bar.foo': [
            'pytest',
            'bar',
            'zoo'
        ]
    }) == [
        'foo  # from collection foo.bar',
        'bar  # from collection foo.bar,bar.foo',
        'zoo  # from collection bar.foo'
    ]


def test_skip_bad_formats():
    """A single incorrectly formatted requirement should warn, but not block other reqs"""
    assert sanitize_python_requirements({'foo.bar': [
        'foo',
        'bar'
    ], 'foo.bad': ['zizzer zazzer zuzz']  # not okay
    }) == ['foo  # from collection foo.bar', 'bar  # from collection foo.bar']


@pytest.mark.parametrize('lines,expect', [
    ([], []),
    (['subversion'], [('subversion', [], [])]),
    (['subversion', ''], [('subversion', [], [])]),
    (['python [platform:brew] ==3.7.3,>2.0'], [
        ('python', [(True, 'platform:brew')], [('==', '3.7.3'), ('>', '2.0')])
    ]),

])
def test_parse_bindep_lines(lines, expect):
    data = parse_bindep_lines(lines)
    assert data == expect
    assert render_bindep_data(data) == '\n'.join(lines).strip()


def test_sanitize_system_requirements():
    input = {
        'test.bindep': [
            '# this is a comment',
            'subversion [platform:rpm]',
            'subversion [platform:dpkg]'
        ],
        'repeat.collection': [
            'subversion [platform:rpm]',
        ],
        'notgood.collection': [
            'python [platform:rpm]'
        ]
    }
    sanitized = sanitize_system_requirements(input)
    assert sanitized == [
        'subversion [platform:rpm]  # from collection test.bindep,repeat.collection',
        'subversion [platform:dpkg]  # from collection test.bindep'
    ]


def test_incorrect_bindep():
    input = {
        'test.bindep': [
            'at [platform:rpm'  # unbalanced brackets
        ]
    }
    with pytest.raises(Exception):
        sanitize_system_requirements(input)
