import argparse
import sys
import yaml

from . import __version__

from .colors import MessageColors
from .exceptions import DefinitionError
from .main import AnsibleBuilder
from . import constants
from .introspect import add_introspect_options, process, simple_combine
from .requirements import sanitize_requirements


def run():
    args = parse_args()
    if args.action in ['build']:
        ab = AnsibleBuilder(**vars(args))
        action = getattr(ab, ab.action)
        try:
            if action():
                print(MessageColors.OKGREEN + "Complete! The build context can be found at: {0}".format(ab.build_context) + MessageColors.ENDC)
                sys.exit(0)
        except DefinitionError as e:
            print(e.args[0])
            sys.exit(1)
    elif args.action == 'introspect':
        data = process(args.folder)
        if args.sanitize:
            data['python'] = sanitize_requirements(data['python'])
            data['system'] = simple_combine(data['system'])
            print()
            print('# Sanitized dependencies for {0}'.format(args.folder))
        else:
            print()
            print('# Dependency data for {0}'.format(args.folder))
        print('---')
        print(yaml.dump(data, default_flow_style=False))
        sys.exit(0)

    print(MessageColors.FAIL + "An error has occured." + MessageColors.ENDC)
    sys.exit(1)


def parse_args(args=sys.argv[1:]):
    parser = argparse.ArgumentParser(
        prog='ansible-builder',
        description=(
            'Tooling to help build container images for running Ansible content. '
            'Get started by looking at the help text for one of the subcommands.'
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
                                      help='The name for the container image being built.')

    for p in [build_command_parser]:

        p.add_argument('-f', '--file',
                       default=constants.default_file,
                       dest='filename',
                       help='The definition of the execution environment.')

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
                       help='Specifies which container runtime to use. Defaults to podman.')

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
    introspect_parser.add_argument(
        '--sanitize', help=(
            'Sanitize and de-duplicate requirements. '
            'This is normally done separately from the introspect script, but this '
            'option is given to more accurately test collection content.'
        ), action='store_true'
    )

    args = parser.parse_args(args)

    return args
