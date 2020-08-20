from ansible_builder.requirements import sanitize_requirements


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
