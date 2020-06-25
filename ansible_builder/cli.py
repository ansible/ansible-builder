import argparse
import sys

from .main import AnsibleBuilder


def prepare(args=sys.argv[1:]):
    parser = argparse.ArgumentParser(prog='ansible-builder')
    subparsers = parser.add_subparsers(help='The command to invoke.')

    create_command_parser = subparsers.add_parser('create',
                                                  help='Outputs a build context, including a Containerfile, populated with dependencies.')

    build_command_parser = subparsers.add_parser('build',
                                                 help='Builds the container with the Containerfile that got created via "create" command.')

    build_command_parser.add_argument('-t', '--tag',
                                      default='ansible-execution-env:latest',
                                      help='The name for the container being built.')

    build_command_parser.add_argument('--container-runtime',
                                      default='podman',
                                      help='Specifies which container runtime to use.')

    for p in [create_command_parser, build_command_parser]:

        p.add_argument('-f', '--file',
                       default='execution-environment.yml',
                       dest='filename',
                       help='The definiton of the execution environment.')

        p.add_argument('-b', '--base-image',
                       default='shanemcd/ansible-runner',
                       help='The parent image for the execution environment.')

        p.add_argument('-c', '--context',
                       default=None,
                       dest='build_context',
                       help='The directory to use for the build context. Defaults to $PWD/context.')

    args = parser.parse_args(args)

    return AnsibleBuilder(**vars(args))


def run():
    ab = prepare()

    print('Processing...', end='\r')
    # TO DO: stdout that prints in real-time and/or a "spinner"

    build_or_create = getattr(ab, sys.argv[1])
    if build_or_create():
        print("Complete! Build context is at: {}".format(ab.build_context))
        sys.exit(0)

    print("An error has occured.")
    sys.exit(1)
