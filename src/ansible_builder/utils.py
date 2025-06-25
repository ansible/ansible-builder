import filecmp
import logging
import logging.config
import os
import shutil
import subprocess
import sys

from collections import deque
from pathlib import Path

from .colors import MessageColors
from . import constants


logger = logging.getLogger(__name__)
logging_levels = {
    '0': 'ERROR',
    '1': 'WARNING',
    '2': 'INFO',
    '3': 'DEBUG',
}


class ColorFilter(logging.Filter):
    color_map = {
        'ERROR': MessageColors.FAIL,
        'WARNING': MessageColors.WARNING,
        'INFO': MessageColors.HEADER,
        'DEBUG': MessageColors.OK
    }

    def filter(self, record):
        if sys.stdout.isatty():
            record.msg = self.color_map[record.levelname] + record.msg + MessageColors.ENDC
        return record


LOGGING = {
    'version': 1,
    'filters': {
        'colorize': {
            '()': ColorFilter
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'filters': ['colorize'],
            'stream': 'ext://sys.stdout'
        }
    },
    'loggers': {
        'ansible_builder': {
            'handlers': ['console'],
        }
    }
}


def configure_logger(verbosity):
    LOGGING['loggers']['ansible_builder']['level'] = logging_levels[str(verbosity)]
    logging.config.dictConfig(LOGGING)


def run_command(command, capture_output=False, allow_error=False):
    logger.info('Running command:')
    logger.info('  %s', ' '.join(command))
    try:
        # pylint: disable=R1732
        process = subprocess.Popen(command,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT)
    except FileNotFoundError:
        msg = f"You do not have {command[0]} installed."
        if command[0] in constants.runtime_files:
            blurb = {True: 'installed', False: 'not installed'}
            install_summary = ', '.join([
                f'{runtime}: {blurb.get(bool(shutil.which(runtime)))}' for runtime in constants.runtime_files
            ])
            msg += (
                f'\nYou do not have {command[0]} installed.\n'
                f'Please either install {command[0]} or specify an alternative container '
                f'runtime by passing --container-runtime on the command line.\n'
                f'Below are the supported container runtimes and whether '
                f'or not they were found on your system.\n{install_summary}'
            )
        logger.error(msg)
        sys.exit(1)

    output = []
    trailing_output = deque(maxlen=20)
    for line in iter(process.stdout.readline, b''):
        line = line.decode(sys.stdout.encoding)
        if capture_output:
            output.append(line.rstrip())
        trailing_output.append(line.rstrip())
        logger.debug(line.rstrip('\n'))  # line ends added by logger itself
    logger.debug('')

    rc = process.wait()
    if rc is not None and rc != 0 and (not allow_error):
        main_logger = logging.getLogger('ansible_builder')
        if main_logger.level > logging.INFO:
            logger.error('Command that had error:')
            logger.error('  %s', ' '.join(command))
        if main_logger.level > logging.DEBUG:
            if capture_output:
                for line in output:
                    logger.error(line)
                logger.error('')
            else:
                if len(trailing_output) == 20:
                    logger.error('...showing last 20 lines of output...')
                for line in trailing_output:
                    logger.error(line)
                logger.error('')
        logger.error("An error occurred (rc=%s), see output line(s) above for details.", rc)
        sys.exit(1)

    return (rc, output)


def write_file(filename: str, lines: list) -> bool:
    parent_dir = os.path.dirname(filename)
    if parent_dir and not os.path.exists(parent_dir):
        logger.warning('Creating parent directory for %s', filename)
        os.makedirs(parent_dir)
    new_text = '\n'.join(lines)
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            if f.read() == new_text:
                logger.debug("File %s is already up-to-date.", filename)
                return False
            logger.warning('File %s had modifications and will be rewritten', filename)
    with open(filename, 'w') as f:
        f.write(new_text)
    return True


def copy_directory(source_dir: Path, dest: Path):
    """
    Recursively copy a source directory to a path in the context directory.

    In order to not corrupt the build context cache, if it should exist, we
    attempt to copy files within the source directory to the context directory
    if necessary by utilizing copy_file() on each file, rather than a blind
    recursive copy.
    """

    if not source_dir.is_dir():
        raise Exception(f"Expected a directory at '{source_dir}'")

    for child in source_dir.iterdir():
        copy_location = dest / child.name
        if child.is_dir():
            # a subdir of our build destination directory
            copy_location.mkdir(exist_ok=True)
            copy_directory(child, copy_location)
        else:
            copy_file(str(child), str(copy_location))


def copy_file(source: str, dest: str, ignore_mtime: bool = False) -> bool:
    """
    Copy a source file to a destination file within a container runtime context.

    This preserves build cache correctness: the file is only copied if it doesn't exist or has changed.
    Use `copy_directory()` for directories.

    :param source: Source file path.
    :param dest: Destination file path.
    :param ignore_mtime: If True, modification times are ignored in change detection.
    :returns: True if the file was copied, False otherwise.
    :raises: Exception if source or destination is a directory.
    """
    source_path = Path(source)
    dest_path = Path(dest)

    if os.path.abspath(source) == os.path.abspath(dest):
        logger.info("File %s was placed in build context by user, leaving unmodified.", dest)
        return False

    if source_path.is_dir() or dest_path.is_dir():
        raise Exception(f"{'Source' if source_path.is_dir() else 'Destination'} {source} can not be a directory. Please use copy_directory instead.")

    # Handle symlink logic
    if source_path.is_symlink():
        source_target = os.readlink(source)

        if dest_path.is_symlink():
            dest_target = os.readlink(dest)
            if source_target == dest_target:
                logger.debug("Symlink %s already exists and matches.", dest)
                return False
            logger.debug("Symlink %s target differs and will be overwritten.", dest)
        elif dest_path.exists():
            logger.debug("Destination %s is a regular file and will be replaced by symlink.", dest)

        should_copy = True

    else:
        # Regular file logic
        if not dest_path.exists():
            logger.debug("File %s will be created.", dest)
            should_copy = True
        elif not ignore_mtime and os.path.getmtime(source) > os.path.getmtime(dest):
            logger.warning("File %s updated time increased and will be rewritten", dest)
            should_copy = True
        elif not filecmp.cmp(source_path, dest_path, shallow=False):
            logger.warning("File %s had modifications and will be rewritten", dest)
            should_copy = True
        else:
            should_copy = False

    if should_copy:
        if dest_path.is_symlink() or dest_path.exists():
            os.unlink(dest)

        if source_path.is_symlink():
            os.symlink(os.readlink(source), dest)
        else:
            shutil.copy2(source, dest)

    else:
        logger.debug("File %s is already up-to-date.", dest)

    return should_copy
