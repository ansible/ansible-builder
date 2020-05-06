import argparse
import sys

from .main import AnsibleExecEnv


def prepare(args=sys.argv[1:]):
    parser = argparse.ArgumentParser(prog='ansible-exec-env')
    subparsers = parser.add_subparsers(help='The command to invoke.')

    build_command_parser = subparsers.add_parser('build', help='Outputs a Containerfile, populated with resolved dependencies.')
    build_command_parser.add_argument('-f', '--file', default='execution-environment.yml', help='The definiton file', dest='filename')
    build_command_parser.add_argument('-b', '--base-image', default='shanemcd/ansible-runner', help='The parent image for the execution environment')
    build_command_parser.add_argument('-c', '--context', default=None, dest='build_context')

    args = parser.parse_args(args)

    return AnsibleExecEnv(**vars(args))


def run():
    aee = prepare()

    print('Processing...', end='\r')

    if aee.process():
        print("Complete! Build context is at: {}".format(aee.build_context))
        sys.exit(0)

    print("An error has occured.")
    sys.exit(1)
