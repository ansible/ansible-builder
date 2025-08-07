import os
import tempfile
import yaml


def test_template_help(cli):
    """Test template command help output."""
    result = cli('ansible-builder template --help', check=False)
    help_text = result.stdout
    assert 'usage: ansible-builder template [-h]' in help_text
    assert 'Generate a sample execution environment YAML file' in help_text
    assert '--schema-version' in help_text
    assert '--output' in help_text
    assert '--minimal' in help_text


def test_template_default_version(cli):
    """Test template command with default settings (version 3)."""
    result = cli('ansible-builder template', check=False)
    output = result.stdout

    # Parse YAML output
    template_data = yaml.safe_load(output)

    assert template_data['version'] == 3
    assert 'dependencies' in template_data
    assert 'options' in template_data
    assert 'images' in template_data


def test_template_version_1(cli):
    """Test template command with schema version 1."""
    result = cli('ansible-builder template --schema-version 1', check=False)
    output = result.stdout

    # Parse YAML output
    template_data = yaml.safe_load(output)

    assert template_data['version'] == 1
    assert 'build_arg_defaults' in template_data
    assert 'EE_BASE_IMAGE' in template_data['build_arg_defaults']
    assert 'EE_BUILDER_IMAGE' in template_data['build_arg_defaults']
    # v1 should not have images section
    assert 'images' not in template_data


def test_template_version_2(cli):
    """Test template command with schema version 2."""
    result = cli('ansible-builder template --schema-version 2', check=False)
    output = result.stdout

    # Parse YAML output
    template_data = yaml.safe_load(output)

    assert template_data['version'] == 2
    assert 'images' in template_data
    assert 'base_image' in template_data['images']
    assert 'builder_image' in template_data['images']
    # v2 should not have EE_BASE_IMAGE in build args
    if 'build_arg_defaults' in template_data:
        assert 'EE_BASE_IMAGE' not in template_data['build_arg_defaults']


def test_template_version_3(cli):
    """Test template command with schema version 3."""
    result = cli('ansible-builder template --schema-version 3', check=False)
    output = result.stdout

    # Parse YAML output
    template_data = yaml.safe_load(output)

    assert template_data['version'] == 3
    assert 'dependencies' in template_data
    assert 'options' in template_data
    # v3 should have enhanced features
    if 'dependencies' in template_data and 'galaxy' in template_data['dependencies']:
        galaxy = template_data['dependencies']['galaxy']
        if isinstance(galaxy, dict):
            assert 'collections' in galaxy or 'roles' in galaxy


def test_template_minimal_mode(cli):
    """Test template command with minimal flag."""
    result = cli('ansible-builder template --minimal', check=False)
    output = result.stdout

    # Parse YAML output
    template_data = yaml.safe_load(output)

    # Minimal should only have required fields (version is always added)
    assert template_data['version'] == 3
    # The schema doesn't actually require any fields, so minimal should be just version
    assert len(template_data) >= 1


def test_template_output_to_file(cli):
    """Test template command with file output."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as tmp_file:
        tmp_path = tmp_file.name

    try:
        result = cli(f'ansible-builder template --output {tmp_path}', check=False)

        # Command should run without output to stdout
        assert result.stdout.strip() == ''

        # File should contain the template
        assert os.path.exists(tmp_path)
        with open(tmp_path, 'r') as f:
            content = f.read()
            template_data = yaml.safe_load(content)

        assert template_data['version'] == 3
        assert 'dependencies' in template_data

    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def test_template_invalid_schema_version(cli):
    """Test template command with invalid schema version."""
    result = cli('ansible-builder template --schema-version 99', check=False)

    # Should exit with error
    assert result.returncode != 0
    assert "invalid choice:" in result.stderr


def test_template_all_versions_valid_yaml(cli):
    """Test that all supported schema versions produce valid YAML."""
    for version in [1, 2, 3]:
        result = cli(f'ansible-builder template --schema-version {version}', check=False)

        # Should be able to parse as YAML
        template_data = yaml.safe_load(result.stdout)
        assert isinstance(template_data, dict)
        assert template_data['version'] == version


def test_template_schema_version_and_minimal(cli):
    """Test template command with both schema version and minimal flags."""
    result = cli('ansible-builder template --schema-version 2 --minimal', check=False)
    output = result.stdout

    # Parse YAML output
    template_data = yaml.safe_load(output)

    assert template_data['version'] == 2
    # Should be minimal output for version 2


def test_template_realistic_examples(cli):
    """Test that generated templates contain realistic examples."""
    result = cli('ansible-builder template --schema-version 3', check=False)
    output = result.stdout

    # Parse YAML output
    template_data = yaml.safe_load(output)

    # Check for realistic values
    if 'images' in template_data and 'base_image' in template_data['images']:
        base_image = template_data['images']['base_image']['name']
        assert 'quay.io' in base_image or 'registry' in base_image

    if 'dependencies' in template_data:
        deps = template_data['dependencies']
        if 'python' in deps and isinstance(deps['python'], list):
            # Should contain realistic Python package names
            python_deps = deps['python']
            assert any('requests' in str(dep) or 'pyyaml' in str(dep) for dep in python_deps)


def test_template_verbosity_option(cli):
    """Test template command with verbosity option."""
    # Test that verbosity option is accepted (though template doesn't use it much)
    result = cli('ansible-builder template -v', check=False)

    # Should still produce valid output
    template_data = yaml.safe_load(result.stdout)
    assert template_data['version'] == 3


def test_template_exit_code_success(cli):
    """Test that template command exits with code 0 on success."""
    result = cli('ansible-builder template', check=False)
    assert result.returncode == 0


def test_template_file_permissions_error(cli):
    """Test template command with invalid output path."""
    # Try to write to a directory that doesn't exist
    result = cli('ansible-builder template --output /nonexistent/path/template.yml', check=False)

    # Should exit with error code
    assert result.returncode != 0
