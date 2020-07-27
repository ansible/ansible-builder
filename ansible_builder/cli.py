import argparse
import sys
import yaml

from . import __version__

from .colors import MessageColors
from .main import AnsibleBuilder, DefinitionError
from . import constants
from .introspect import add_introspect_options, process


def prepare(args=sys.argv[1:]):
    args = parse_args(args)
    return AnsibleBuilder(**vars(args))


def run():
    args = parse_args()
    if args.action in ['build']:
        ab = AnsibleBuilder(**vars(args))
        action = getattr(ab, ab.action)
        try:
            if action():
                print(MessageColors.OKGREEN + "Complete! The build context can be found at: {}".format(ab.build_context) + MessageColors.ENDC)
                sys.exit(0)
        except DefinitionError as e:
            print(MessageColors.FAIL + e.args[0] + MessageColors.ENDC)
            sys.exit(1)
    elif args.action == 'introspect':
        for folder in args.folders:
            data = process(folder)
            print()
            print('Dependency data for {0}'.format(folder))
            print(yaml.dump(data, default_flow_style=False))
        sys.exit(0)

    print(MessageColors.FAIL + "An error has occured." + MessageColors.ENDC)
    sys.exit(1)


def parse_args(args=sys.argv[1:]):
    parser = argparse.ArgumentParser(
        prog='ansible-builder',
        description=(
            'Tooling to help build container images for running Ansible content. '
            'Get started by looking at the help for one of the subcommands.'
        )
    )
    parser.add_argument(
        '--version', action='version', version=__version__,
        help='Print ansible-builder version and exit.'
    )
    subparsers = parser.add_subparsers(help='The command to invoke.', dest='action')
    subparsers.required = True # This can be a kwarg in python 3.7+

    build_command_parser = subparsers.add_parser(
        'build',
        help='Builds a container image.',
        description=(
            'Creates a build context (including a Containerfile) from an execution environment spec. '
            'The build context will be populated from the execution environment spec. '
            'After that, the specified container runtime podman/docker will be invoked to '
            'build an image from that definition. '
            'After building the image, it can be used locally or published using the supplied tag.'
        )
    )

    build_command_parser.add_argument('-t', '--tag',
                                      default=constants.default_tag,
                                      help='The name for the container being built.')

    for p in [build_command_parser]:

        p.add_argument('-f', '--file',
                       default=constants.default_file,
                       dest='filename',
                       help='The definiton of the execution environment.')

        p.add_argument('-b', '--base-image',
                       default=constants.default_base_image,
                       help='The parent image for the execution environment.')

        p.add_argument('-c', '--context',
                       default=constants.default_build_context,
                       dest='build_context',
                       help='The directory to use for the build context. Defaults to $PWD/context.')

        p.add_argument('--container-runtime',
                       choices=list(constants.runtime_files.keys()),
                       default=constants.default_container_runtime,
                       help='Specifies which container runtime to use; use for both "build" and "create" commands. '
                       'Defaults to podman.')

    introspect_parser = subparsers.add_parser(
        'introspect',
        help='Introspects collections in folder.',
        description=(
            'Loops over collections in folder and returns data about dependencies. '
            'This is used internally and exposed here for verification. '
            'This is targeted toward collection authors and maintainers.'
        )
    )
    add_introspect_options(introspect_parser)

    args = parser.parse_args(args)

    return args
