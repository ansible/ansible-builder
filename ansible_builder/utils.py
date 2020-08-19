import subprocess
import sys
import os

from .colors import MessageColors


def run_command(command, capture_output=False):
    print(MessageColors.HEADER + 'Running command:' + MessageColors.ENDC)
    print(MessageColors.HEADER + '  {0}'.format(' '.join(command)) + MessageColors.ENDC)

    process = subprocess.Popen(command,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT)

    output = []
    for line in iter(process.stdout.readline, b''):
        line = line.decode(sys.stdout.encoding)
        if capture_output:
            output.append(line.rstrip())
        sys.stdout.write(line)

    rc = process.poll()
    if rc is not None and rc != 0:
        print(MessageColors.FAIL + f"An error occured (rc={rc}), see output line(s) above for details." + MessageColors.ENDC)
        sys.exit(1)

    return (rc, output)


def write_file(filename: str, lines: list) -> bool:
    new_text = '\n'.join(lines)
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            if f.read() == new_text:
                print(MessageColors.OK + "File {0} is already up-to-date.".format(filename) + MessageColors.ENDC)
                return False
            else:
                print(MessageColors.WARNING + 'File {0} had modifications and will be rewritten'.format(filename) + MessageColors.ENDC)
    with open(filename, 'w') as f:
        f.write(new_text)
    return True
