import os

from ansible_builder.utils import write_file


def test_write_file(tmpdir):
    path = os.path.join(tmpdir, 'foo.txt')
    text = [
        'foo  # from some collection',
        'bar',
        '# a comment',
        '',
        'zoo',
        ''  # trailing line
    ]
    assert write_file(path, text)  # does not exist, write
    assert not write_file(path, text)  # already correct, do not write
