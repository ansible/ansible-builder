import filecmp
import logging
import logging.config
import os
import shutil
import subprocess
import sys
from collections import deque

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
        process = subprocess.Popen(command,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT)
    except FileNotFoundError:
        msg = f"You do not have {command[0]} installed."
        if command[0] in constants.runtime_files:
            install_summary = ', '.join([
                '{runtime}: {blurb}'.format(
                    runtime=runtime,
                    blurb={True: 'installed', False: 'not installed'}.get(bool(shutil.which(runtime)))
                ) for runtime in constants.runtime_files
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
        logger.error("An error occured (rc=%s), see output line(s) above for details.", rc)
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
            else:
                logger.warning('File %s had modifications and will be rewritten', filename)
    with open(filename, 'w') as f:
        f.write(new_text)
    return True


def copy_file(source: str, dest: str) -> bool:
    should_copy = False

    if os.path.abspath(source) == os.path.abspath(dest):
        logger.info("File %s was placed in build context by user, leaving unmodified.", dest)
        return False
    elif not os.path.exists(dest):
        logger.debug("File %s will be created.", dest)
        should_copy = True
    elif not filecmp.cmp(source, dest, shallow=False):
        logger.warning('File %s had modifications and will be rewritten', dest)
        should_copy = True
    elif os.path.getmtime(source) > os.path.getmtime(dest):
        logger.warning('File %s updated time increased and will be rewritten', dest)
        should_copy = True

    if should_copy:
        shutil.copy2(source, dest)
    else:
        logger.debug("File %s is already up-to-date.", dest)

    return should_copy
