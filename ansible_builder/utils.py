import subprocess
import sys

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
    return (rc, output)
