import os

from jsonschema import validate, SchemaError, ValidationError

import ansible_builder.constants as constants
from ansible_builder.exceptions import DefinitionError


TYPE_StringOrListOfStrings = {
    "anyOf": [
        {"type": "string"},
        {
            "type": "array",
            "items": {
                "type": "string"
            }
        }
    ]
}

TYPE_DictOrStringOrListOfStrings = {
    "anyOf": [
        {"type": "object"},
        {"type": "string"},
        {
            "type": "array",
            "items": {
                "type": "string"
            }
        }
    ]
}

############
# Version 1
############

schema_v1 = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "version": {
            "description": "The EE schema version number",
            "type": "number",
        },

        "ansible_config": {
            "type": "string",
        },

        "build_arg_defaults": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "EE_BASE_IMAGE": {
                    "type": "string",
                },
                "EE_BUILDER_IMAGE": {
                    "type": "string",
                },
                "ANSIBLE_GALAXY_CLI_COLLECTION_OPTS": {
                    "type": "string",
                },
                "ANSIBLE_GALAXY_CLI_ROLE_OPTS": {
                    "type": "string",
                },
            },
        },

        "dependencies": {
            "description": "The dependency stuff",
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "python": {
                    "description": "The python dependency file",
                    "type": "string",
                },
                "galaxy": {
                    "description": "The Galaxy dependency file",
                    "type": "string",
                },
                "system": {
                    "description": "The system dependency file",
                    "type": "string",
                },
            },
        },

        "additional_build_steps": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "prepend": TYPE_StringOrListOfStrings,
                "append": TYPE_StringOrListOfStrings,
            },
        },
    },
}


############
# Version 2
############

schema_v2 = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "version": {
            "description": "The EE schema version number",
            "type": "number",
        },

        "ansible_config": {
            "type": "string",
        },

        "build_arg_defaults": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "ANSIBLE_GALAXY_CLI_COLLECTION_OPTS": {
                    "type": "string",
                },
                "ANSIBLE_GALAXY_CLI_ROLE_OPTS": {
                    "type": "string",
                },
            },
        },

        "dependencies": {
            "description": "The dependency stuff",
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "python": {
                    "description": "The python dependency file",
                    "type": "string",
                },
                "galaxy": {
                    "description": "The Galaxy dependency file",
                    "type": "string",
                },
                "system": {
                    "description": "The system dependency file",
                    "type": "string",
                },
            },
        },

        "additional_build_steps": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "prepend": TYPE_StringOrListOfStrings,
                "append": TYPE_StringOrListOfStrings,
            },
        },

        "images": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "base_image": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                        },
                        "signature_original_name": {
                            "type": "string",
                        },
                    },
                },
                "builder_image": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                        },
                        "signature_original_name": {
                            "type": "string",
                        },
                    },
                }
            },
        },
    },
}


############
# Version 3
############

schema_v3 = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "version": {
            "description": "The EE schema version number",
            "type": "number",
        },

        "build_arg_defaults": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "ANSIBLE_GALAXY_CLI_COLLECTION_OPTS": {
                    "type": "string",
                },
                "ANSIBLE_GALAXY_CLI_ROLE_OPTS": {
                    "type": "string",
                },
                "PKGMGR_PRESERVE_CACHE": {
                    "type": "string",
                },
            },
        },

        "dependencies": {
            "description": "The dependency stuff",
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "python": TYPE_StringOrListOfStrings,
                "galaxy": TYPE_DictOrStringOrListOfStrings,
                "system": TYPE_StringOrListOfStrings,
                "python_interpreter": {
                    "description": "Python package name and path",
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "package_system": {
                            "description": "The python package to install via system package manager",
                            "type": "string",
                        },
                        "python_path": {
                            "description": "Path to the python interpreter",
                            "type": "string",
                        },
                    },
                },
                "ansible_core": {
                    "description": "Ansible package installation",
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "package_pip": {
                            "description": "Ansible package to install via pip",
                            "type": "string",
                        },
                    },
                    "oneOf": [
                        # more to be added later
                        {"required": ["package_pip"]},
                    ],
                },
                "ansible_runner": {
                    "description": "Ansible Runner package installation",
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "package_pip": {
                            "description": "Ansible Runner package to install via pip",
                            "type": "string",
                        },
                    },
                    "oneOf": [
                        # more to be added later
                        {"required": ["package_pip"]},
                    ],
                },
            },
        },

        "images": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "base_image": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                        },
                        "signature_original_name": {
                            "type": "string",
                        },
                    },
                },
            },
        },

        "additional_build_steps": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "prepend_base": TYPE_StringOrListOfStrings,
                "append_base": TYPE_StringOrListOfStrings,
                "prepend_galaxy": TYPE_StringOrListOfStrings,
                "append_galaxy": TYPE_StringOrListOfStrings,
                "prepend_builder": TYPE_StringOrListOfStrings,
                "append_builder": TYPE_StringOrListOfStrings,
                "prepend_final": TYPE_StringOrListOfStrings,
                "append_final": TYPE_StringOrListOfStrings,
            },
        },

        "additional_build_files": {
            "description": "Describes files to add to the build context",
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "src": {
                        "description": "File to add to build context",
                        "type": "string",
                    },
                    "dest": {
                        "description": "Relative subdirectory under build context to place file",
                        "type": "string",
                    },
                },
                "required": ["src", "dest"],
            },
        },

        "options": {
            "description": "Options that effect runtime behavior",
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "relax_passwd_permissions": {
                    "description": "allows GID0 write access to /etc/passwd; currently necessary for many uses",
                    "type": "boolean",
                },
                "skip_ansible_check": {
                    "description": "Disables the check for Ansible/Runner in final image",
                    "type": "boolean",
                },
                "workdir": {
                    "description": "Default working directory, also often the homedir for ephemeral UIDs",
                    "type": ["string", "null"],
                },
                "package_manager_path": {
                    "description": "Path to the system package manager to use",
                    "type": "string",
                },
                "user": {
                    "description": "Sets the username or UID",
                    "type": "string",
                },
                "container_init": {
                    "description": "Customize container startup behavior",
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "package_pip": {
                            "description": "package to install via pip for entrypoint support",
                            "type": "string",
                        },
                        "entrypoint": {
                            "description": "literal value for ENTRYPOINT Containerfile directive",
                            "type": "string",
                        },
                        "cmd": {
                            "description": "literal value for CMD Containerfile directive",
                            "type": "string",
                        },
                    },
                },
            },
        },
    },
}


def validate_schema(ee_def: dict):
    schema_version = 1
    if 'version' in ee_def:
        try:
            schema_version = int(ee_def['version'])
        except ValueError:
            raise DefinitionError(f"Schema version not an integer: {ee_def['version']}")

    if schema_version not in (1, 2, 3):
        raise DefinitionError(f"Unsupported schema version: {schema_version}")

    try:
        if schema_version == 1:
            validate(instance=ee_def, schema=schema_v1)
        elif schema_version == 2:
            validate(instance=ee_def, schema=schema_v2)
        elif schema_version == 3:
            validate(instance=ee_def, schema=schema_v3)
    except (SchemaError, ValidationError) as e:
        raise DefinitionError(msg=e.message, path=e.absolute_schema_path)

    _handle_aliasing(ee_def)

    if schema_version >= 3:
        _handle_options_defaults(ee_def)


def _handle_aliasing(ee_def: dict):
    """
    Upgrade EE keys into standard keys across schema versions.

    Some EE keys are renamed across schema versions. So that we don't need to
    check schema version, or do some other hackery, in the builder code when
    accessing the values, just do the key name upgrades/aliasing here.
    """

    if 'additional_build_steps' in ee_def:
        # V1/V2 'prepend' == V3 'prepend_final'
        if 'prepend' in ee_def['additional_build_steps']:
            ee_def['additional_build_steps']['prepend_final'] = ee_def['additional_build_steps']['prepend']

        # V1/V2 'append' == V3 'append_final'
        if 'append' in ee_def['additional_build_steps']:
            ee_def['additional_build_steps']['append_final'] = ee_def['additional_build_steps']['append']


def _handle_options_defaults(ee_def: dict):
    """
    JSONSchema can document a "default" value, but it isn't used for validation.
    This method is used to set any default values for the "options" dictionary
    properties.
    """
    options = ee_def.setdefault('options', {})

    entrypoint_path = os.path.join(constants.FINAL_IMAGE_BIN_PATH, "entrypoint")

    options.setdefault('skip_ansible_check', False)
    options.setdefault('relax_passwd_permissions', True)
    options.setdefault('workdir', '/runner')
    options.setdefault('package_manager_path', '/usr/bin/dnf')
    options.setdefault('container_init', {
        'package_pip': 'dumb-init==1.2.5',
        'entrypoint': f'["{entrypoint_path}", "dumb-init"]',
        'cmd': '["bash"]',
    })
    options.setdefault('user', '1000')
