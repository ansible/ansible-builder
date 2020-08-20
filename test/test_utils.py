import os

from ansible_builder.utils import write_file, copy_file


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


def test_copy_file(tmpdir):
    dest = os.path.join(tmpdir, 'foo.txt')
    source = os.path.join(tmpdir, 'bar.txt')
    with open(source, 'w') as f:
        f.write('foo\nbar\n')
    assert copy_file(source, dest)
    assert not copy_file(source, dest)

    with open(source, 'w') as f:
        f.write('foo\nbar\nzoo')
    assert copy_file(source, dest)
