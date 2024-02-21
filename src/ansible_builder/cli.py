import argparse
import logging
import sys
import os
import importlib.metadata

from . import constants

from .colors import MessageColors
from .exceptions import DefinitionError
from .main import AnsibleBuilder
from .policies import PolicyChoices
from ._target_scripts.introspect import create_introspect_parser, run_introspect
from .utils import configure_logger


logger = logging.getLogger(__name__)


def run():
    args = parse_args()
    configure_logger(args.verbosity)

    if args.action in ['create', 'build']:
        ab = AnsibleBuilder(**vars(args))
        action = getattr(ab, ab.action)
        try:
            if action():
                print(
                    MessageColors.OKGREEN + "Complete! The build context can be found at: {0}".format(
                        os.path.abspath(ab.build_context)
                    ) + MessageColors.ENDC)
                sys.exit(0)
        except DefinitionError as e:
            logger.error(e.args[0])
            sys.exit(1)

    elif args.action == 'introspect':
        run_introspect(args, logger)

    logger.error("An error has occurred.")
    sys.exit(1)


def get_version():
    return importlib.metadata.version('ansible_builder')


def add_container_options(parser):
    """
    Add sub-commands and options relevant to containers.
    """
    create_command_parser = parser.add_parser(
        'create',
        help='Creates a build context, which can be used by podman to build an image.',
        description=(
            'Creates a build context (including a Containerfile) from an execution environment spec. '
            'This build context is populated with dependencies including requirements files.'
        )
    )

    build_command_parser = parser.add_parser(
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

    # Because of the way argparse works, if we specify the default here, it would
    # always be included in the value list if a tag value was supplied. We don't want
    # that, so we must, instead, set the default AFTER the argparse.parse_args() call.
    # See https://bugs.python.org/issue16399 for more info.
    build_command_parser.add_argument(
        '-t', '--tag',
        action='extend',
        nargs='+',
        help=f'The name(s) for the container image being built (default: {constants.default_tag})')

    build_command_parser.add_argument(
        '--container-runtime',
        choices=list(constants.runtime_files.keys()),
        default=constants.default_container_runtime,
        help='Specifies which container runtime to use (default: %(default)s)')

    build_command_parser.add_argument(
        '--build-arg',
        action=BuildArgAction,
        default={},
        dest='build_args',
        help='Build-time variables to pass to any podman or docker calls. '
             'Internally ansible-builder makes use of {0}.'.format(
             ', '.join(constants.build_arg_defaults.keys())))

    build_command_parser.add_argument(
        '--no-cache',
        action='store_true',
        help='Do not use cache when building the image',
    )

    build_command_parser.add_argument(
        '--prune-images',
        action='store_true',
        help='Remove all dangling images after building the image',
    )

    build_command_parser.add_argument(
        '--container-policy',
        choices=[p.value for p in PolicyChoices],
        default=None,
        help='Container image validation policy.',
    )

    build_command_parser.add_argument(
        '--container-keyring',
        help='GPG keyring for container image validation.',
    )

    build_command_parser.add_argument(
        '--squash',
        choices=['new', 'all', 'off'],
        default='off',
        help='Squash layers in the final image (choices: %(choices)s). Defaults to "%(default)s". (podman only)'
    )

    for p in [create_command_parser, build_command_parser]:

        p.add_argument('-f', '--file',
                       default=constants.default_file,
                       dest='filename',
                       help='The definition of the execution environment (default: %(default)s)')

        p.add_argument('-c', '--context',
                       default=constants.default_build_context,
                       dest='build_context',
                       help='The directory to use for the build context (default: %(default)s)')

        p.add_argument('--output-filename',
                       choices=list(constants.runtime_files.values()),
                       default=None,
                       help='Name of file to write image definition to '
                            '(default depends on --container-runtime, {0})'.format(
                                ' and '.join([' for '.join([v, k]) for k, v in constants.runtime_files.items()]))
                       )

        p.add_argument('--galaxy-keyring',
                       help='Keyring for collection signature verification during installs from Galaxy. '
                            'Will be copied into images. Verification is disabled if unset.')
        p.add_argument('--galaxy-ignore-signature-status-codes',
                       action="append",
                       help='A gpg status code to ignore during signature verification when installing with '
                       'ansible-galaxy. May be specified multiple times. See ansible-galaxy doc for more info.')
        p.add_argument('--galaxy-required-valid-signature-count',
                       help='The number of signatures that must successfully verify collections from '
                       'ansible-galaxy ~if there are any signatures provided~. See ansible-galaxy doc for more info.')

    introspect_parser = create_introspect_parser(parser)

    for n in [create_command_parser, build_command_parser, introspect_parser]:

        n.add_argument('-v', '--verbosity',
                       dest='verbosity',
                       type=int,
                       choices=[0, 1, 2, 3],
                       default=constants.default_verbosity,
                       help='Increase the output verbosity, for up to three levels of verbosity '
                            '(invoked via "--verbosity" or "-v" followed by an integer ranging '
                            'in value from 0 to 3) (default: %(default)s)')


def parse_args(args=None):

    parser = argparse.ArgumentParser(
        prog='ansible-builder',
        description=(
            'Tooling to help build container images for running Ansible content. '
            'Get started by looking at the help text for one of the subcommands.'
        )
    )
    parser.add_argument(
        '--version', action='version', version=get_version(),
        help='Print ansible-builder version and exit.'
    )

    subparsers = parser.add_subparsers(
        help='The command to invoke.',
        dest='action',
        required=True,
    )

    add_container_options(subparsers)

    args = parser.parse_args(args)

    # Tag default must be handled differently. See comment for --tag option.
    if 'tag' not in vars(args) or not args.tag:
        args.tag = [constants.default_tag]

    return args


class BuildArgAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        key, sep, value = values.partition("=")
        attr = getattr(namespace, self.dest)

        # None signifies that the build-arg will come from the environment.
        # This is currently only supported by Docker. Podman will treat any
        # usage of the $VALUE as a literal string.
        if value:
            attr[key] = value
        elif sep == '=' and value == '':
            attr[key] = ''
        else:
            attr[key] = None
