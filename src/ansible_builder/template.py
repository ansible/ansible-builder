import sys
from typing import Dict, Any, Optional, TextIO

import yaml

from . import ee_schema


def generate_template_from_schema(schema_dict: Dict[str, Any], version: int, minimal: bool = False) -> Dict[str, Any]:
    """
    Generate a sample YAML structure from a JSON schema.

    Args:
        schema_dict: The JSON schema dictionary
        version: Schema version number to use for the version field
        minimal: If True, only include required fields

    Returns:
        Dictionary representing the sample YAML structure
    """
    template: Dict[str, Any] = {}

    if 'properties' not in schema_dict:
        return template

    properties = schema_dict['properties']
    required_fields = schema_dict.get('required', [])

    for field_name, field_schema in properties.items():
        if minimal and field_name not in required_fields:
            continue

        template[field_name] = _generate_value_from_schema(field_name, field_schema, version, minimal)

    return template


def _generate_value_from_schema(field_name: str, field_schema: Dict[str, Any], version: int,
                                minimal: bool = False) -> Any:
    """Generate a sample value based on the field schema."""

    # Handle anyOf (like TYPE_StringOrListOfStrings)
    if 'anyOf' in field_schema:
        # Choose the first option that's a string type for simplicity
        for option in field_schema['anyOf']:
            if option.get('type') == 'string':
                return _generate_string_value(field_name)
        # Fallback to first option
        return _generate_value_from_schema(field_name, field_schema['anyOf'][0], version, minimal)

    field_type = field_schema.get('type')

    if field_type == 'string':
        return _generate_string_value(field_name)
    if field_type == 'number':
        return _generate_number_value(field_name, version)
    if field_type == 'boolean':
        return _generate_boolean_value(field_name)
    if field_type == 'array':
        items_schema = field_schema.get('items', {})
        if items_schema.get('type') == 'string':
            return _generate_string_array_value(field_name)
        if items_schema.get('type') == 'object':
            sample_item = _generate_value_from_schema(field_name, items_schema, version, minimal)
            return [sample_item]
        return []
    if field_type == 'object':
        return generate_template_from_schema(field_schema, version, minimal)
    if isinstance(field_type, list):
        # Handle type arrays like ["string", "null"]
        for t in field_type:
            if t != "null":
                return _generate_value_from_schema(field_name, {"type": t}, version, minimal)

    return None


def _generate_string_value(field_name: str) -> str:
    """Generate appropriate string values based on field name."""

    string_samples = {
        'ansible_config': 'ansible.cfg',
        'python': 'requirements.txt',
        'galaxy': 'requirements.yml',
        'system': 'bindep.txt',
        'package_system': 'python39',
        'python_path': '/usr/bin/python3.9',
        'package_pip': 'ansible-core>=2.12',
        'package_manager_path': '/usr/bin/dnf',
        'workdir': '/runner',
        'user': '1000',
        'entrypoint': '["entrypoint", "dumb-init"]',
        'cmd': '["bash"]',
        'src': 'files/config.cfg',
        'dest': 'configs',
        'ANSIBLE_GALAXY_CLI_COLLECTION_OPTS': '--pre',
        'ANSIBLE_GALAXY_CLI_ROLE_OPTS': '--ignore-errors',
        'PKGMGR_PRESERVE_CACHE': 'always'
    }

    # Special handling for image names
    if field_name == 'name':
        return 'quay.io/ansible/ee-minimal:latest'
    if field_name == 'signature_original_name':
        return 'registry.redhat.io/ansible-automation-platform-21/ee-minimal-rhel8:latest'

    # Check for exact matches first
    if field_name in string_samples:
        return string_samples[field_name]

    # Check for partial matches
    if 'image' in field_name.lower():
        return 'quay.io/ansible/ee-minimal:latest'
    if 'path' in field_name.lower():
        return '/usr/bin/example'
    if 'package' in field_name.lower():
        return 'example-package>=1.0'
    if 'user' in field_name.lower():
        return '1000'

    return f'example-{field_name.lower()}'


def _generate_number_value(field_name: str, version: int) -> int:
    """Generate appropriate number values based on field name."""
    if field_name == 'version':
        return version
    return 1


def _generate_boolean_value(field_name: str) -> bool:
    """Generate appropriate boolean values based on field name."""
    # Most boolean options default to False for safety
    boolean_defaults = {
        'relax_passwd_permissions': True,
        'skip_ansible_check': False,
        'skip_pip_install': False
    }
    return boolean_defaults.get(field_name, False)


def _generate_string_array_value(field_name: str) -> list:
    """Generate appropriate string array values based on field name."""

    array_samples = {
        'python': ['requests>=2.25.0', 'pyyaml>=5.4.0'],
        'system': ['git', 'rsync'],
        'collections': ['community.general', 'ansible.posix'],
        'roles': ['example.role1', 'example.role2'],
        'tags': ['my-ee:latest', 'my-ee:v1.0']
    }

    if field_name in array_samples:
        return array_samples[field_name]

    # Check for partial matches
    if 'python' in field_name.lower():
        return ['requests>=2.25.0']
    if 'system' in field_name.lower():
        return ['git']
    if 'collection' in field_name.lower():
        return ['community.general']
    if 'role' in field_name.lower():
        return ['example.role']
    if 'tag' in field_name.lower():
        return ['my-ee:latest']

    return [f'example-{field_name.lower()}']


def generate_execution_environment_template(version: int = 3, minimal: bool = False) -> Dict[str, Any]:
    """
    Generate a complete execution environment template for the specified schema version.

    Args:
        version: Schema version (1, 2, or 3)
        minimal: If True, only include required fields

    Returns:
        Dictionary representing the complete template
    """
    if version == 1:
        schema = ee_schema.schema_v1
    elif version == 2:
        schema = ee_schema.schema_v2
    elif version == 3:
        schema = ee_schema.schema_v3
    else:
        raise ValueError(f"Unsupported schema version: {version}. Supported versions: 1, 2, 3")

    template = generate_template_from_schema(schema, version, minimal)

    # Ensure version is always set correctly
    template['version'] = version

    # Add some customization for better examples
    if not minimal:
        template = _enhance_template_examples(template, version)

    return template


def _enhance_template_examples(template: Dict[str, Any], version: int) -> Dict[str, Any]:
    """Enhance the template with better examples and structure."""

    # For version 3, provide more comprehensive examples
    if version == 3:
        if 'dependencies' in template and isinstance(template['dependencies'], dict):
            deps = template['dependencies']

            # Enhance galaxy section to show both collections and roles
            if 'galaxy' in deps:
                deps['galaxy'] = {
                    'collections': ['community.general', 'ansible.posix'],
                    'roles': ['example.role1', 'example.role2']
                }

            # Enhance exclude section with better examples
            if 'exclude' in deps and isinstance(deps['exclude'], dict):
                deps['exclude'] = {
                    'python': ['outdated-package'],
                    'system': ['unnecessary-package'],
                    'all_from_collections': ['collection.with.conflicts']
                }

        # Enhance additional_build_files with better examples
        if 'additional_build_files' in template:
            template['additional_build_files'] = [
                {'src': 'files/ansible.cfg', 'dest': 'configs'},
                {'src': 'files/custom-scripts/', 'dest': 'scripts'}
            ]

    return template


def write_template_to_file(template: Dict[str, Any], output_file: Optional[TextIO] = None) -> None:
    """
    Write the template to a file or stdout as YAML.

    Args:
        template: The template dictionary to write
        output_file: File handle to write to, defaults to stdout
    """
    if output_file is None:
        output_file = sys.stdout

    # Use safe_dump for clean YAML output
    yaml.safe_dump(
        template,
        output_file,
        default_flow_style=False,
        sort_keys=False,
        indent=2,
        allow_unicode=True
    )


def run_template(args) -> None:
    """
    Main function to handle the template command.

    Args:
        args: Parsed command line arguments
    """
    try:
        template = generate_execution_environment_template(
            version=args.schema_version,
            minimal=args.minimal
        )

        if args.output:
            with open(args.output, 'w') as f:
                write_template_to_file(template, f)
        else:
            write_template_to_file(template)

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)
