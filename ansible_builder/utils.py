import subprocess


def run_command(command):
    print('Running command:')
    print('  {0}'.format(' '.join(command)))
    result = subprocess.run(command)
    return bool(result.returncode == 0)
