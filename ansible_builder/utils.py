import filecmp
import logging
import logging.config
import os
import shutil
import subprocess
import sys

from .colors import MessageColors


logger = logging.getLogger('builder')
logging_levels = {
    '0': logging.ERROR,
    '1': logging.WARNING,
    '2': logging.INFO,
    '3': logging.DEBUG,
}


class MyFilter(logging.Filter):
    def filter(self, record):
        record.msg = 'Hi mom!'
        return 1


LOGGING = {
    'version': 1,
    'filters': {
        'myfilter': {
            '()': MyFilter,
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        }
    },
    'builder': {
        'handlers': ['console']
    },
}


def configure_logger(verbosity):
    # logging.basicConfig(stream=sys.stdout, level=logging_levels[str(verbosity)], format='%(message)s')
    # create console handler with a higher log level
    LOGGING['builder']['level'] = logging_levels[str(verbosity)]
    logging.config.dictConfig(LOGGING)



def run_command(command, capture_output=False, allow_error=False):
    logger.info(MessageColors.HEADER + 'Running command:' + MessageColors.ENDC)
    logger.info(MessageColors.HEADER + '  {0}'.format(' '.join(command)) + MessageColors.ENDC)

    process = subprocess.Popen(command,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT)

    output = []
    for line in iter(process.stdout.readline, b''):
        line = line.decode(sys.stdout.encoding)
        if capture_output:
            output.append(line.rstrip())
        logger.debug(line)

    rc = process.poll()
    if rc is not None and rc != 0 and (not allow_error):
        logger.error(MessageColors.FAIL + f"An error occured (rc={rc}), see output line(s) above for details." + MessageColors.ENDC)
        sys.exit(1)

    return (rc, output)


def write_file(filename: str, lines: list) -> bool:
    new_text = '\n'.join(lines)
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            if f.read() == new_text:
                logger.debug(MessageColors.OK + "File {0} is already up-to-date.".format(filename) + MessageColors.ENDC)
                return False
            else:
                logger.warning(MessageColors.WARNING + 'File {0} had modifications and will be rewritten'.format(filename) + MessageColors.ENDC)
    with open(filename, 'w') as f:
        f.write(new_text)
    return True


def copy_file(source: str, dest: str) -> bool:
    should_copy = False

    if not os.path.exists(dest):
        logger.debug(MessageColors.OK + "File {0} will be created.".format(dest) + MessageColors.ENDC)
        should_copy = True
    elif not filecmp.cmp(source, dest, shallow=False):
        logger.warning(MessageColors.WARNING + 'File {0} had modifications and will be rewritten'.format(dest) + MessageColors.ENDC)
        should_copy = True
    elif os.path.getmtime(source) > os.path.getmtime(dest):
        logger.warning(MessageColors.WARNING + 'File {0} updated time increased and will be rewritten'.format(dest) + MessageColors.ENDC)
        should_copy = True

    if should_copy:
        shutil.copy(source, dest)
    else:
        logger.debug(MessageColors.OK + "File {0} is already up-to-date.".format(dest) + MessageColors.ENDC)

    return should_copy
