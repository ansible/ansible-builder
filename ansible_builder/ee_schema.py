from jsonschema import validate, SchemaError, ValidationError

from ansible_builder.exceptions import DefinitionError


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
                "prepend": {
                    "anyOf": [{"type": "string"}, {"type": "array"}],
                },
                "append": {
                    "anyOf": [{"type": "string"}, {"type": "array"}],
                },
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

        "additional_build_steps": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "prepend": {
                    "anyOf": [{"type": "string"}, {"type": "array"}],
                },
                "append": {
                    "anyOf": [{"type": "string"}, {"type": "array"}],
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

    if schema_version not in (1, 2):
        raise DefinitionError(f"Unsupported schema version: {schema_version}")

    try:
        if schema_version == 1:
            validate(instance=ee_def, schema=schema_v1)
        elif schema_version == 2:
            validate(instance=ee_def, schema=schema_v2)
    except (SchemaError, ValidationError) as e:
        raise DefinitionError(msg=e.message, path=e.absolute_schema_path)
