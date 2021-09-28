import os
import time
from pathlib import Path

import pytest

from ansible_builder.utils import write_file, copy_file, run_command


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


@pytest.fixture
def source_file(tmpdir):
    source = os.path.join(tmpdir, 'bar.txt')
    with open(source, 'w') as f:
        f.write('foo\nbar\n')
    return source


@pytest.fixture
def dest_file(tmpdir, source_file):
    '''Returns a file that has been copied from source file
    Use of fixture partially tests the copy_file functionality
    '''
    dest = os.path.join(tmpdir, 'foo.txt')
    assert copy_file(source_file, dest)
    assert not copy_file(source_file, dest)
    return dest


def test_copy_file(dest_file, source_file):
    # modify source file, which should trigger a re-copy
    with open(source_file, 'w') as f:
        f.write('foo\nbar\nzoo')

    assert copy_file(source_file, dest_file)
    assert not copy_file(source_file, dest_file)


def test_copy_touched_file(dest_file, source_file):
    # sleep for a miniscule amount of time, otherwise getmtime could be the same float value
    time.sleep(0.002)

    # touch does not change contents but updates modification time
    Path(source_file).touch()

    assert copy_file(source_file, dest_file)
    assert not copy_file(source_file, dest_file)


@pytest.mark.run_command
def test_failed_command(mocker):
    mocker.patch('ansible_builder.utils.subprocess.Popen.wait', return_value=1)
    with pytest.raises(SystemExit):
        run_command(['sleep', '--invalidargument'])


@pytest.mark.run_command
def test_failed_command_with_allow_error(mocker):
    mocker.patch('ansible_builder.utils.subprocess.Popen.wait', return_value=1)

    rc, out = run_command(
        ['sleep', '--invalidargument'],
        allow_error=True,
    )

    assert rc == 1
    assert out == []


@pytest.mark.run_command
def test_invalid_non_docker_command(caplog, mocker):
    mocker.patch('ansible_builder.utils.subprocess.Popen.wait', return_value=1)

    command = 'thisisnotacommand'
    with pytest.raises(SystemExit):
        run_command([command], capture_output=True)

    record = caplog.records[-1]  # final log message emitted

    assert f'You do not have {command} installed' in record.msg
    assert 'container-runtime' not in record.msg


@pytest.mark.run_command
def test_invalid_docker_command(caplog, mocker):
    mocker.patch('ansible_builder.utils.subprocess.Popen', side_effect=FileNotFoundError)
    mocker.patch('ansible_builder.utils.shutil.which', return_value=False)

    with pytest.raises(SystemExit):
        run_command(['docker', 'history', 'quay.io/foo/fooooo'], capture_output=True)

    record = caplog.records[-1]  # final log message emitted

    assert 'You do not have docker installed' in record.msg
    assert 'podman: not installed, docker: not installed' in record.msg
