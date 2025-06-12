from __future__ import annotations

import functools
import logging
import os
import textwrap
import tempfile
from pathlib import Path
from typing import Callable

import yaml

from . import constants
from .exceptions import DefinitionError
from .ee_schema import validate_schema
from .utils import set_default_file_permissions


logger = logging.getLogger(__name__)

# HACK: manage lifetimes more carefully
_tempfiles: list[Callable] = []


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

    def __init__(self, filename=None):
        """
        Initialize the UserDefinition object.

        :param str filename: Path to the EE file. If this is None, we will
            look for the default file: execution-environment.(yml|yaml)
        """

        # A dict that is the raw representation of the EE file.
        self.raw = {}

        if filename is None:
            for ext in constants.YAML_FILENAME_EXTENSIONS:
                ee_file = f'{constants.DEFAULT_EE_BASENAME}.{ext}'
                if os.path.exists(ee_file):
                    filename = ee_file
                    break
            if filename is None:
                raise DefinitionError(textwrap.dedent(
                    """
                    Default execution environment file not found in current directory.
                    Use -f to specify the correct file.
                    """))

        self.filename = filename

        # The folder which dependencies are specified relative to.
        self.reference_path = os.path.dirname(self.filename)

        try:
            with open(self.filename, 'r') as ee_file:
                data = yaml.safe_load(ee_file)
                self.raw = data if data else {}
        except FileNotFoundError as exc:
            raise DefinitionError(textwrap.dedent(
                f"""
                Could not detect '{self.filename}' file in this directory.
                Use -f to specify a different location.
                """)) from exc
        except (yaml.parser.ParserError, yaml.scanner.ScannerError) as exc:
            raise DefinitionError(f"An error occurred while parsing the definition file:\n{str(exc)}") from exc

        if not isinstance(self.raw, dict):
            raise DefinitionError(f"Definition must be a dictionary, not {type(self.raw).__name__}")

        # Set default values for the build arguments. User supplied values
        # are set later during validation.
        self.build_arg_defaults = constants.build_arg_defaults.copy()
        if self.version > 2:
            # v3 and higher no longer supports a builder image so make
            # sure this value is cleared of the default value.
            self.build_arg_defaults['EE_BUILDER_IMAGE'] = None

        # Attributes used for creating podman container policies. These will be None
        # if no 'images' section is present in the EE, or an ImageDescription object otherwise.
        self.base_image = None
        self.builder_image = None

    @property
    def version(self):
        """
        Integer version of the EE file.

        If no version is specified, assume version 1 (for backward compat).
        """
        version = self.raw.get('version', 1)
        return version

    @property
    def ansible_config(self):
        """ Path to the user specified ansible.cfg file """
        ansible_config = self.raw.get('ansible_config')
        if not ansible_config:
            return None
        return str(ansible_config)

    @property
    def additional_build_steps(self):
        """Gets additional commands from the exec env file, if any are specified.
        """
        return self.raw.get('additional_build_steps')

    @property
    def python_package_system(self):
        return self.raw.get('dependencies', {}).get('python_interpreter', {}).get('package_system', None)

    @property
    def python_path(self):
        return self.raw.get('dependencies', {}).get('python_interpreter', {}).get('python_path', None)

    @property
    def ansible_core_ref(self):
        return self.raw.get('dependencies', {}).get('ansible_core', {}).get('package_pip', None)

    @property
    def ansible_runner_ref(self):
        return self.raw.get('dependencies', {}).get('ansible_runner', {}).get('package_pip', None)

    @property
    def ansible_ref_install_list(self):
        return ' '.join([r for r in (self.ansible_core_ref, self.ansible_runner_ref) if r]) or None

    @property
    def additional_build_files(self):
        return self.raw.get('additional_build_files', [])

    @property
    def container_init(self):
        return self.raw.get('options', {}).get('container_init', {})

    @property
    def options(self):
        return self.raw.get('options', {})

    @property
    def dependencies(self):
        return self.raw.get('dependencies', {})

    # This is the size of galaxy, python, system * exclude=True/False
    @functools.lru_cache(maxsize=6)
    def get_dep_abs_path(self, entry, exclude=False):
        """Unique to the user EE definition, files can be referenced by either
        an absolute path or a path relative to the EE definition folder
        This method will return the absolute path.
        """
        deps = self.dependencies
        if exclude:
            deps = deps.get('exclude', {})

        req_file = deps.get(entry)

        if not req_file:
            return None

        # dump inline-declared deps to files that will be injected directly into the generated context
        if isinstance(req_file, dict):
            tf = tempfile.NamedTemporaryFile('w')
            tf.write(yaml.safe_dump(req_file))
            tf.flush()  # don't close, it'll clean up on GC
            _tempfiles.append(tf)
            req_file = tf.name
            set_default_file_permissions(req_file)
        elif (is_list := isinstance(req_file, list)) or (isinstance(req_file, str) and '\n' in req_file):
            # pylint: disable=R1732
            tf = tempfile.NamedTemporaryFile('w')
            if is_list:
                tf.write('\n'.join(req_file))
            else:
                tf.write(req_file)
            _tempfiles.append(tf)
            tf.flush()  # don't close, it'll clean up on GC
            req_file = tf.name
            set_default_file_permissions(req_file)
        if not isinstance(req_file, str):
            return None

        if os.path.isabs(req_file):
            return req_file

        return os.path.join(self.reference_path, req_file)

    def _validate_additional_build_files(self):
        """
        Check that entries in additional_build_files look correct.

        The 'dest' values are checked for the correct format. Since 'src' can
        be a file glob or an absolute or relative path, it is not checked.

        :raises: DefinitionError exception if any errors are found.
        """
        for entry in self.additional_build_files:
            dest = Path(entry['dest'])
            if dest.is_absolute() or '..' in dest.parts:
                raise DefinitionError(f"'dest' must not be an absolute path or contain '..': {dest}")

    def validate(self):
        """
        Check that all specified keys in the definition file are valid.

        :raises: DefinitionError exception if any errors are found.
        """
        validate_schema(self.raw)

        for item in constants.CONTEXT_FILES:
            for exclude in (False, True):
                requirement_path = self.get_dep_abs_path(item, exclude=exclude)
                if requirement_path:
                    if not os.path.exists(requirement_path):
                        raise DefinitionError(f"Dependency file {requirement_path} does not exist.")

        # Validate and set any user-specified build arguments
        build_arg_defaults = self.raw.get('build_arg_defaults')
        if build_arg_defaults:
            for key, user_value in build_arg_defaults.items():
                self.build_arg_defaults[key] = user_value

        if self.version > 1:
            images = self.raw.get('images', {})
            if images:
                self.base_image = ImageDescription(images, 'base_image')

                # Must set these values so that Containerfile uses the proper images
                if self.base_image.name:
                    self.build_arg_defaults['EE_BASE_IMAGE'] = self.base_image.name
                if 'builder_image' in images:
                    self.builder_image = ImageDescription(images, 'builder_image')
                    self.build_arg_defaults['EE_BUILDER_IMAGE'] = self.builder_image.name

            if (
                self.version >= 3
                and self.build_arg_defaults["EE_BASE_IMAGE"] == 'quay.io/ansible/ansible-runner:latest'
            ):
                logging.warning(
                    "Using the outdated base image '%s' might "
                    "result in the build failures.", self.build_arg_defaults['EE_BASE_IMAGE']
                )

            self._validate_additional_build_files()

            if self.version >= 3:
                build_steps = self.raw.get('additional_build_steps', {})
                for step_name, steps in build_steps.items():
                    for directive in steps:
                        if directive.startswith('USER '):
                            logging.warning(
                                "Found USER directive in '%s' in 'additional_build_steps'. "
                                "Including this directive may cause failures in the build process.", step_name)
