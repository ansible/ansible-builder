import os
import textwrap
import yaml

from . import constants
from .exceptions import DefinitionError


ALLOWED_KEYS_V1 = [
    'version',
    'build_arg_defaults',
    'dependencies',
    'ansible_config',
    'additional_build_steps',
]

ALLOWED_KEYS_V2 = [
    'images',
]


class ImageDescription:
    """
    Class to describe a container image from the EE file.

    For the currently supported 'exactReference' type, this class is dead
    simple. If we deem that we need to support more types, this class may
    become more complex.
    """

    def __init__(self, ee_images, image_key):
        """
        Create an object based on the 'images' portion of the EE definition file.

        :param dict ee_images: The 'images' portion of the EE file.
        :param str image_key: The section (one of 'base_image' or 'builder_image')
            of the 'images' dict to parse.

        :raises: ValueError for an invalid image_key value (programmer error),
            or DefinitionError for invalid EE syntax or missing image tag.
        """
        self.name = None
        self.signature_original_name = None

        if image_key not in ('base_image', 'builder_image'):
            raise ValueError(f"Invalid image key used for initialization: {image_key}")

        image = ee_images.get(image_key)
        if image:
            self.name = image.get('name')
            if not self.name:
                raise DefinitionError(f"'name' is a required field for '{image_key}'")
            self.signature_original_name = image.get('signature_original_name')

        # Validate that the images look like they have a tag.
        for image in (self.name, self.signature_original_name):
            if image:
                data = image.split(':', maxsplit=1)
                if len(data) != 2 or not data[1]:
                    raise DefinitionError(f"Container image requires a tag: {image}")


class UserDefinition:
    """
    Class representing the Execution Environment file.
    """

    def __init__(self, filename):
        """
        Initialize the UserDefinition object.

        :param str filename: Path to the EE file.
        """
        self.filename = filename

        # A dict that is the raw representation of the EE file.
        self.raw = {}
        # The folder which dependencies are specified relative to.
        self.reference_path = os.path.dirname(filename)

        try:
            with open(filename, 'r') as ee_file:
                data = yaml.safe_load(ee_file)
                self.raw = data if data else {}
        except FileNotFoundError as exc:
            raise DefinitionError(textwrap.dedent(
                f"""
                Could not detect '{filename}' file in this directory.
                Use -f to specify a different location.
                """)) from exc
        except (yaml.parser.ParserError, yaml.scanner.ScannerError) as exc:
            raise DefinitionError(f"An error occurred while parsing the definition file:\n{str(exc)}") from exc

        if not isinstance(self.raw, dict):
            raise DefinitionError(f"Definition must be a dictionary, not {type(self.raw).__name__}")

        # Set default values for the build arguments. User supplied values
        # are set later during validation.
        self.build_arg_defaults = constants.build_arg_defaults.copy()

        # Attributes used for creating podman container policies. These will be None
        # if no 'images' section is present in the EE, or an ImageDescription object otherwise.
        self.base_image = None
        self.builder_image = None

    @property
    def version(self):
        """
        Version of the EE file.

        If no version is specified, assume version 1 (for backward compat).
        """
        version = self.raw.get('version', 1)
        return str(version)

    @property
    def ansible_config(self):
        """ Path to the user specified ansible.cfg file """
        ansible_config = self.raw.get('ansible_config')
        if not ansible_config:
            return None
        return str(ansible_config)

    def get_additional_commands(self):
        """Gets additional commands from the exec env file, if any are specified.
        """
        commands = self.raw.get('additional_build_steps')
        return commands

    def get_dep_abs_path(self, entry):
        """Unique to the user EE definition, files can be referenced by either
        an absolute path or a path relative to the EE definition folder
        This method will return the absolute path.
        """
        req_file = self.raw.get('dependencies', {}).get(entry)

        if not req_file:
            return None

        if os.path.isabs(req_file):
            return req_file

        return os.path.join(self.reference_path, req_file)

    def _validate_root_keys(self):
        """
        Identify any invalid top-level keys in the execution environment file.

        :raises: DefinitionError exception if any invalid keys are identified.
        """
        def_file_dict = self.raw
        yaml_keys = set(def_file_dict.keys())

        valid_keys = set(ALLOWED_KEYS_V1)
        if self.version == '2':
            valid_keys = valid_keys.union(set(ALLOWED_KEYS_V2))

        invalid_keys = yaml_keys - valid_keys

        if invalid_keys:
            raise DefinitionError(textwrap.dedent(
                f"""
                Error: Unknown yaml key(s), {invalid_keys}, found in the definition file.\n
                Allowed options are:
                {valid_keys}
                """)
            )

    def _validate_v2(self):
        """
        Validate all execution environment file, version 2, keys.

        :raises: DefinitionError exception if any errors are found.
        """

        if self.version == "1":
            return

        images = self.raw.get('images', {})

        # The base and builder images MUST be defined in the 'images' section only.
        bad = self.raw.get('build_arg_defaults')
        if bad:
            if 'EE_BASE_IMAGE' in bad or 'EE_BUILDER_IMAGE' in bad:
                raise DefinitionError("Error: Version 2 does not allow defining EE_BASE_IMAGE or EE_BUILDER_IMAGE in 'build_arg_defaults'")

        if images:
            self.base_image = ImageDescription(images, 'base_image')
            self.builder_image = ImageDescription(images, 'builder_image')

            # Must set these values so that Containerfile uses the proper images
            self.build_arg_defaults['EE_BASE_IMAGE'] = self.base_image.name
            self.build_arg_defaults['EE_BUILDER_IMAGE'] = self.builder_image.name

    def _validate_v1(self):
        """
        Validate all execution environment file, version 1, keys.

        :raises: DefinitionError exception if any errors are found.
        """

        if self.raw.get('dependencies') is not None:
            if not isinstance(self.raw.get('dependencies'), dict):
                raise DefinitionError(textwrap.dedent(
                    f"""
                    Error: Unknown type {type(self.raw.get('dependencies'))} found for dependencies, must be a dict.\n
                    Allowed options are:
                    {list(constants.CONTEXT_FILES.keys())}
                    """)
                )

            dependencies_keys = set(self.raw.get('dependencies'))
            invalid_dependencies_keys = dependencies_keys - set(constants.CONTEXT_FILES.keys())
            if invalid_dependencies_keys:
                raise DefinitionError(textwrap.dedent(
                    f"""
                    Error: Unknown yaml key(s), {invalid_dependencies_keys}, found in dependencies.\n
                    Allowed options are:
                    {list(constants.CONTEXT_FILES.keys())}
                    """)
                )

        for item in constants.CONTEXT_FILES:
            requirement_path = self.get_dep_abs_path(item)
            if requirement_path:
                if not os.path.exists(requirement_path):
                    raise DefinitionError(f"Dependency file {requirement_path} does not exist.")

        # Validate and set any user-specified build arguments
        build_arg_defaults = self.raw.get('build_arg_defaults')
        if build_arg_defaults:
            if not isinstance(build_arg_defaults, dict):
                raise DefinitionError(
                    f"Error: Unknown type {type(build_arg_defaults)} found for build_arg_defaults; "
                    f"must be a dict."
                )
            unexpected_keys = set(build_arg_defaults) - set(constants.build_arg_defaults)
            if unexpected_keys:
                raise DefinitionError(
                    f"Keys {unexpected_keys} are not allowed in 'build_arg_defaults'."
                )
            for key, user_value in build_arg_defaults.items():
                if user_value and not isinstance(user_value, str):
                    raise DefinitionError(
                        f"Expected build_arg_defaults.{key} to be a string; "
                        f"Found a {type(user_value)} instead."
                    )
                self.build_arg_defaults[key] = user_value

        additional_cmds = self.get_additional_commands()
        if additional_cmds:
            if not isinstance(additional_cmds, dict):
                raise DefinitionError(textwrap.dedent("""
                    Expected 'additional_build_steps' in the provided definition file to be a dictionary
                    with keys 'prepend' and/or 'append'; found a {0} instead.
                    """).format(type(additional_cmds).__name__))

            expected_keys = frozenset(('append', 'prepend'))
            unexpected_keys = set(additional_cmds) - expected_keys
            if unexpected_keys:
                raise DefinitionError(
                    f"Keys {*unexpected_keys,} are not allowed in 'additional_build_steps'."
                )

        ansible_config_path = self.raw.get('ansible_config')
        if ansible_config_path:
            if not isinstance(ansible_config_path, str):
                raise DefinitionError(textwrap.dedent(f"""
                    Expected 'ansible_config' in the provided definition file to
                    be a string; found a {type(ansible_config_path).__name__} instead.
                    """))

    def validate(self):
        """
        Check that all specified keys in the definition file are valid.

        :raises: DefinitionError exception if any errors are found.
        """

        self._validate_root_keys()
        self._validate_v1()
        self._validate_v2()
