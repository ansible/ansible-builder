import os
import textwrap
import yaml

from . import constants
from .exceptions import DefinitionError


ALLOWED_KEYS = [
    'version',
    'build_arg_defaults',
    'dependencies',
    'ansible_config',
    'additional_build_steps',
]


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
        except FileNotFoundError:
            raise DefinitionError(textwrap.dedent(f"""
            Could not detect '{filename}' file in this directory.
            Use -f to specify a different location.
            """))
        except (yaml.parser.ParserError, yaml.scanner.ScannerError) as exc:
            raise DefinitionError(f"An error occurred while parsing the definition file:\n{str(exc)}")

        if not isinstance(self.raw, dict):
            raise DefinitionError(f"Definition must be a dictionary, not {type(self.raw).__name__}")

        if self.raw.get('dependencies') is not None:
            if not isinstance(self.raw.get('dependencies'), dict):
                raise DefinitionError(textwrap.dedent(
                    f"""
                    Error: Unknown type {type(self.raw.get('dependencies'))} found for dependencies, must be a dict.\n
                    Allowed options are:
                    {list(constants.CONTEXT_FILES.keys())}
                    """)
                )

        # Populate build arg defaults, which are customizable in definition
        self.build_arg_defaults = {}
        user_build_arg_defaults = self.raw.get('build_arg_defaults', {})
        if not isinstance(user_build_arg_defaults, dict):
            user_build_arg_defaults = {}  # so that validate method can throw error
        for key, default_value in constants.build_arg_defaults.items():
            self.build_arg_defaults[key] = user_build_arg_defaults.get(key, default_value)

    @property
    def version(self):
        """ Version of the EE file """
        version = self.raw.get('version')
        if not version:
            raise ValueError("Expected top-level 'version' key to be present.")
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

    def validate(self):
        """
        Check that all specified keys in the definition file are valid.
        """

        def_file_dict = self.raw
        yaml_keys = set(def_file_dict.keys())
        invalid_keys = yaml_keys - set(ALLOWED_KEYS)
        if invalid_keys:
            raise DefinitionError(textwrap.dedent(
                f"""
                Error: Unknown yaml key(s), {invalid_keys}, found in the definition file.\n
                Allowed options are:
                {ALLOWED_KEYS}
                """)
            )

        if self.raw.get('dependencies') is not None:
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

        build_arg_defaults = self.raw.get('build_arg_defaults')
        if build_arg_defaults:
            if not isinstance(build_arg_defaults, dict):
                raise DefinitionError(
                    f"Error: Unknown type {type(build_arg_defaults)} found for build_arg_defaults; "
                    f"must be a dict."
                )
            unexpected_keys = set(build_arg_defaults.keys()) - set(constants.build_arg_defaults)
            if unexpected_keys:
                raise DefinitionError(
                    f"Keys {unexpected_keys} are not allowed in 'build_arg_defaults'."
                )
            for key in constants.build_arg_defaults:
                user_value = build_arg_defaults.get(key)
                if user_value and not isinstance(user_value, str):
                    raise DefinitionError(
                        f"Expected build_arg_defaults.{key} to be a string; "
                        f"Found a {type(user_value)} instead."
                    )

        additional_cmds = self.get_additional_commands()
        if additional_cmds:
            if not isinstance(additional_cmds, dict):
                raise DefinitionError(textwrap.dedent("""
                    Expected 'additional_build_steps' in the provided definition file to be a dictionary
                    with keys 'prepend' and/or 'append'; found a {0} instead.
                    """).format(type(additional_cmds).__name__))

            expected_keys = frozenset(('append', 'prepend'))
            unexpected_keys = set(additional_cmds.keys()) - expected_keys
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
