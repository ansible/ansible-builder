from ansible_builder._target_scripts.introspect import sanitize_requirements


def test_combine_entries():
    assert sanitize_requirements({
        'foo.bar': ['foo>1.0'],
        'bar.foo': ['foo>=2.0']
    }) == ['foo>1.0,>=2.0  # from collection foo.bar,bar.foo']


def test_remove_unwanted_requirements():
    assert sanitize_requirements({
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
    assert sanitize_requirements({'foo.bar': [
        'foo',
        'bar'
    ], 'foo.bad': ['zizzer zazzer zuzz']  # not okay
    }) == ['foo  # from collection foo.bar', 'bar  # from collection foo.bar']


def test_sanitize_requirements_do_not_exclude():
    py_reqs = {
        'foo.bar': [
            'foo',
            'ansible',   # should not appear
            'bar',
        ],
        'user': [
            'pytest',    # should appear
            'bar',
            'zoo'
        ]
    }

    assert sanitize_requirements(py_reqs) == [
        'foo  # from collection foo.bar',
        'bar  # from collection foo.bar,user',
        'pytest  # from collection user',
        'zoo  # from collection user',
    ]
