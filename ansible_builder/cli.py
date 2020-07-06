import argparse
import sys

from . import __version__

from .main import AnsibleBuilder
from . import constants


def prepare(args=sys.argv[1:]):
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
    # TODO: Need to have a paragraph come up when running `ansible-builder -h` that explains what Builder is/does
    subparsers = parser.add_subparsers(help='The command to invoke.', dest='action')
    subparsers.required = True # This can be a kwarg in python 3.7+

    create_command_parser = subparsers.add_parser(
        'create',
        help='Creates a build context, which can be used by podman to build an image.',
        description=(
            'Creates a build context (including a Containerfile) from an execution environment spec. '
            'This build context is populated with dependencies including requirements files.'
        )
    )

    build_command_parser = subparsers.add_parser(
        'build',
        help='Builds a container image.',
        description=(
            'This does everything that the "create" command does, and then builds the image. '
            'The build context will be populated from the execution environment spec. '
            'After that, the specified container runtime podman/docker will be invoked to '
            'build an image from that definition. '
            'After building the image, it can be used locally or published using the supplied tag.'
        )
    )
    # TODO: Need to update the docstrings for the create and build commands to be more specific/helpful

    build_command_parser.add_argument('-t', '--tag',
                                      default=constants.default_tag,
                                      help='The name for the container being built.')

    for p in [create_command_parser, build_command_parser]:

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

    args = parser.parse_args(args)

    return AnsibleBuilder(**vars(args))


def run():
    ab = prepare()

    print('Processing...')

    build_or_create = getattr(ab, ab.action)
    if build_or_create():
        print("Complete! Build context is at: {}".format(ab.build_context))
        sys.exit(0)

    print("An error has occured.")
    sys.exit(1)
