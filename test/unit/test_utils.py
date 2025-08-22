import filecmp
import os
import pathlib

import pytest

from ansible_builder.utils import configure_logger, write_file, copy_directory, copy_file, run_command


def assert_file(path: pathlib.Path, expected_text: str):
    assert path.exists()
    assert not path.is_symlink()
    assert path.read_text() == expected_text


def assert_symlink(path: pathlib.Path, target_path: pathlib.Path):
    assert path.exists()
    assert path.is_symlink()
    assert os.readlink(path) == str(target_path)


def test_write_file(tmp_path):
    path = tmp_path / 'bar' / 'foo.txt'
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


def test_copy_file(dest_file, source_file):
    # modify source file, which should trigger a re-copy
    source_file.write_text('foo\nbar\nzoo')

    assert copy_file(source_file, dest_file)
    assert not copy_file(source_file, dest_file)
    assert not copy_file(source_file, source_file)


def test_copy_touched_file(dest_file, source_file):
    stat = pathlib.Path(source_file).stat()
    new_atime = stat.st_atime + 1
    new_mtime = stat.st_mtime + 1
    os.utime(source_file, (new_atime, new_mtime))

    assert copy_file(source_file, dest_file)
    assert not copy_file(source_file, dest_file)


def test_copy_touched_file_ignore_mtime(dest_file, source_file):
    stat = pathlib.Path(source_file).stat()
    new_atime = stat.st_atime + 1
    new_mtime = stat.st_mtime + 1
    os.utime(source_file, (new_atime, new_mtime))

    assert not copy_file(source_file, dest_file, ignore_mtime=True)


def test_copy_file_with_destination_directory(dest_file, source_file):
    # Change source file to trigger copy_file
    source_file.write_text('foo\nbar\nzoo')

    with pytest.raises(Exception) as err:
        copy_file(source_file, '/tmp')
    assert "can not be a directory" in str(err.value.args[0])

    with pytest.raises(Exception) as err:
        copy_file('/tmp', dest_file)
    assert "can not be a directory" in str(err.value.args[0])

    assert copy_file(source_file, dest_file)


@pytest.mark.run_command
def test_failed_command(mocker):
    mocker.patch('ansible_builder.utils.subprocess.Popen.wait', return_value=1)
    configure_logger(3)
    with pytest.raises(SystemExit):
        run_command(['sleep', '--invalidargument'], capture_output=True)


@pytest.mark.run_command
def test_failed_command_with_allow_error(mocker):
    mocker.patch('ansible_builder.utils.subprocess.Popen.wait', return_value=1)

    rc, out = run_command(
        ['sleep', '--invalidargument'],
        allow_error=True,
    )

    assert rc == 1
    assert not out


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


def test_copy_directory_notadir(tmp_path):
    """
    Test passing a file instead of a directory.
    """
    notadir = tmp_path / 'xyz'
    notadir.touch()
    with pytest.raises(Exception, match="Expected a directory at *"):
        copy_directory(notadir, 'abc')


def test_copy_directory(tmp_path):
    src = tmp_path / "src"
    src.mkdir()

    # a file
    src_f1 = src / "f1"
    src_f1.touch()

    # a subdirectory and a file underneath it
    src_d1 = src / "d1"
    src_d1.mkdir()
    src_d1f2 = src_d1 / "f2"
    src_d1f2.touch()

    dst = tmp_path / "dst"
    dst.mkdir()

    copy_directory(src, dst)

    dcmp = filecmp.dircmp(str(src), str(dst))
    assert not dcmp.left_only
    assert not dcmp.right_only


def test_regular_to_missing(tmp_path):
    source = tmp_path / "source.txt"
    source.write_text("abc")
    dest = tmp_path / "dest.txt"

    # First copy
    copied = copy_file(str(source), str(dest))
    assert copied is True
    assert_file(dest, "abc")

    # Second copy - no changes
    copied = copy_file(str(source), str(dest))
    assert copied is False
    assert_file(dest, "abc")


def test_symlink_to_missing(tmp_path):
    target = tmp_path / "target.txt"
    target.write_text("abc")
    source = tmp_path / "source_symlink"
    os.symlink(target, source)

    dest = tmp_path / "dest"

    # Before Copy
    assert_symlink(source, target)
    assert not dest.exists()

    copied = copy_file(str(source), str(dest))
    assert copied is True
    assert_symlink(source, target)
    assert_symlink(dest, target)

    copied = copy_file(str(source), str(dest))
    assert copied is False
    assert_symlink(source, target)
    assert_symlink(dest, target)


def test_symlink_to_same_symlink(tmp_path):
    target = tmp_path / "target.txt"
    target.write_text("abc")
    source = tmp_path / "source_symlink"
    dest = tmp_path / "dest_symlink"
    os.symlink(target, source)
    os.symlink(target, dest)

    # Before Copy
    assert_symlink(source, target)
    assert_symlink(dest, target)

    copied = copy_file(str(source), str(dest))
    assert copied is False
    assert_symlink(source, target)
    assert_symlink(dest, target)

    copied = copy_file(str(source), str(dest))
    assert copied is False
    assert_symlink(source, target)
    assert_symlink(dest, target)


def test_symlink_to_different_symlink(tmp_path):
    target1 = tmp_path / "target1.txt"
    target2 = tmp_path / "target2.txt"
    target1.write_text("abc")
    target2.write_text("def")

    source = tmp_path / "source_symlink"
    dest = tmp_path / "dest_symlink"
    os.symlink(target1, source)
    os.symlink(target2, dest)

    # Before Copy
    assert_symlink(source, target1)
    assert_symlink(dest, target2)

    copied = copy_file(str(source), str(dest))
    assert copied is True
    assert_symlink(source, target1)
    assert_symlink(dest, target1)

    copied = copy_file(str(source), str(dest))
    assert copied is False
    assert_symlink(source, target1)
    assert_symlink(dest, target1)


def test_symlink_overwrites_regular_file(tmp_path):
    target = tmp_path / "target.txt"
    target.write_text("abc")
    source = tmp_path / "source_symlink"
    os.symlink(target, source)

    dest = tmp_path / "dest.txt"
    dest.write_text("def")  # existing regular file

    # Before Copy
    assert_symlink(source, target)
    assert_file(dest, "def")

    copied = copy_file(str(source), str(dest))
    assert copied is True
    assert_symlink(source, target)
    assert_symlink(dest, target)

    copied = copy_file(str(source), str(dest))
    assert copied is False
    assert_symlink(source, target)
    assert_symlink(dest, target)


def test_regular_file_overwrites_symlink(tmp_path):
    source = tmp_path / "source.txt"
    source.write_text("abc")

    old_target = tmp_path / "old_target.txt"
    old_target.write_text("def")
    dest = tmp_path / "dest_symlink"
    os.symlink(old_target, dest)

    # Before Copy
    assert_symlink(dest, old_target)
    assert_file(source, "abc")

    copied = copy_file(str(source), str(dest))
    assert copied is True
    assert_file(source, "abc")
    assert_file(dest, "abc")

    # Clear filecmp's cache to ensure the next comparison re-checks file contents
    filecmp.clear_cache()

    copied = copy_file(str(source), str(dest))
    assert copied is False
    assert_file(source, "abc")
    assert_file(dest, "abc")


def test_symlink_broken_target(tmp_path):
    # Broken symlink: still copy as symlink
    target = tmp_path / "missing_target.txt"  # doesn't exist
    source = tmp_path / "broken_symlink"
    os.symlink(target, source)

    dest = tmp_path / "dest"

    copied = copy_file(str(source), str(dest))
    assert copied is True
    assert not source.exists()
    assert not dest.exists()  # Symlink points to a file that does not exist
    assert dest.is_symlink()
    assert os.readlink(dest) == str(target)

    copied = copy_file(str(source), str(dest))
    assert copied is False
    assert not source.exists()
    assert not dest.exists()
    assert dest.is_symlink()
    assert os.readlink(dest) == str(target)
