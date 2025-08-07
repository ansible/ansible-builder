from io import StringIO
from unittest.mock import patch, mock_open

import pytest

from ansible_builder import template


class TestGenerateTemplateFromSchema:
    """Test the generate_template_from_schema function."""

    def test_empty_schema(self):
        """Test with empty schema."""
        result = template.generate_template_from_schema({}, 3)
        assert not result

    def test_schema_without_properties(self):
        """Test with schema that has no properties."""
        schema = {"type": "object"}
        result = template.generate_template_from_schema(schema, 3)
        assert not result

    def test_simple_string_property(self):
        """Test generating a simple string property."""
        schema = {
            "properties": {
                "name": {"type": "string"}
            }
        }
        result = template.generate_template_from_schema(schema, 3)
        assert result == {"name": "quay.io/ansible/ee-minimal:latest"}

    def test_version_property_uses_schema_version(self):
        """Test that version property uses the provided schema version."""
        schema = {
            "properties": {
                "version": {"type": "number"}
            }
        }
        result = template.generate_template_from_schema(schema, 2)
        assert result == {"version": 2}

        result = template.generate_template_from_schema(schema, 1)
        assert result == {"version": 1}

    def test_minimal_mode_only_required(self):
        """Test minimal mode only includes required fields."""
        schema = {
            "properties": {
                "version": {"type": "number"},
                "optional_field": {"type": "string"},
                "required_field": {"type": "string"}
            },
            "required": ["version", "required_field"]
        }
        result = template.generate_template_from_schema(schema, 3, minimal=True)
        assert "version" in result
        assert "required_field" in result
        assert "optional_field" not in result

    def test_anyof_string_selection(self):
        """Test anyOf selects string type when available."""
        schema = {
            "properties": {
                "test_field": {
                    "anyOf": [
                        {"type": "array", "items": {"type": "string"}},
                        {"type": "string"}
                    ]
                }
            }
        }
        result = template.generate_template_from_schema(schema, 3)
        assert isinstance(result["test_field"], str)

    def test_nested_object(self):
        """Test nested object generation."""
        schema = {
            "properties": {
                "nested": {
                    "type": "object",
                    "properties": {
                        "inner_field": {"type": "string"}
                    }
                }
            }
        }
        result = template.generate_template_from_schema(schema, 3)
        assert "nested" in result
        assert isinstance(result["nested"], dict)
        assert "inner_field" in result["nested"]


class TestValueGeneration:
    """Test individual value generation functions."""
    # pylint: disable=protected-access

    def test_generate_string_value_special_cases(self):
        """Test string value generation for special field names."""
        assert template._generate_string_value("name") == "quay.io/ansible/ee-minimal:latest"
        assert template._generate_string_value("package_system") == "python39"
        assert template._generate_string_value("workdir") == "/runner"
        assert template._generate_string_value("user") == "1000"

    def test_generate_string_value_partial_matches(self):
        """Test string value generation for partial matches."""
        assert "quay.io" in template._generate_string_value("base_image_name")
        assert "/usr/bin" in template._generate_string_value("some_path")
        assert "package" in template._generate_string_value("custom_package")

    def test_generate_number_value(self):
        """Test number value generation."""
        assert template._generate_number_value("version", 2) == 2
        assert template._generate_number_value("other_number", 3) == 1

    def test_generate_boolean_value(self):
        """Test boolean value generation."""
        assert template._generate_boolean_value("relax_passwd_permissions") is True
        assert template._generate_boolean_value("skip_ansible_check") is False
        assert template._generate_boolean_value("unknown_field") is False

    def test_generate_string_array_value(self):
        """Test string array value generation."""
        python_deps = template._generate_string_array_value("python")
        assert isinstance(python_deps, list)
        assert len(python_deps) > 0
        assert any("requests" in dep for dep in python_deps)

        collections = template._generate_string_array_value("collections")
        assert isinstance(collections, list)
        assert "community.general" in collections


class TestGenerateExecutionEnvironmentTemplate:
    """Test the main template generation function."""

    def test_unsupported_schema_version(self):
        """Test that unsupported schema versions raise ValueError."""
        with pytest.raises(ValueError, match="Unsupported schema version: 4"):
            template.generate_execution_environment_template(4)

    def test_version_1_template(self):
        """Test generating version 1 template."""
        result = template.generate_execution_environment_template(1)
        assert result["version"] == 1
        assert "build_arg_defaults" in result
        assert "EE_BASE_IMAGE" in result["build_arg_defaults"]
        assert "images" not in result  # v1 doesn't have images section

    def test_version_2_template(self):
        """Test generating version 2 template."""
        result = template.generate_execution_environment_template(2)
        assert result["version"] == 2
        assert "images" in result
        assert "base_image" in result["images"]
        assert "builder_image" in result["images"]

    def test_version_3_template(self):
        """Test generating version 3 template."""
        result = template.generate_execution_environment_template(3)
        assert result["version"] == 3
        assert "dependencies" in result
        assert "options" in result
        assert "additional_build_files" in result

    def test_minimal_template(self):
        """Test generating minimal template."""
        result = template.generate_execution_environment_template(3, minimal=True)
        assert result["version"] == 3
        # Should only have required fields (none are actually required in the schema)
        # But version is always added
        assert len(result) >= 1

    def test_enhanced_examples_v3(self):
        """Test that v3 templates get enhanced examples."""
        result = template.generate_execution_environment_template(3)

        # Check galaxy enhancement
        if "dependencies" in result and "galaxy" in result["dependencies"]:
            galaxy = result["dependencies"]["galaxy"]
            if isinstance(galaxy, dict):
                assert "collections" in galaxy or "roles" in galaxy

        # Check additional_build_files enhancement
        if "additional_build_files" in result:
            build_files = result["additional_build_files"]
            assert isinstance(build_files, list)
            if build_files:
                assert "src" in build_files[0]
                assert "dest" in build_files[0]


class TestWriteTemplateToFile:
    """Test the write_template_to_file function."""

    def test_write_to_stdout(self):
        """Test writing template to stdout."""
        template_dict = {"version": 3, "test": "value"}

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            template.write_template_to_file(template_dict)
            output = mock_stdout.getvalue()

        assert "version: 3" in output
        assert "test: value" in output

    def test_write_to_file(self):
        """Test writing template to file."""
        template_dict = {"version": 3, "test": "value"}
        mock_file = StringIO()

        template.write_template_to_file(template_dict, mock_file)
        output = mock_file.getvalue()

        assert "version: 3" in output
        assert "test: value" in output


class TestRunTemplate:
    """Test the run_template function."""

    def test_run_template_stdout(self):
        """Test run_template with stdout output."""
        # Mock args object
        class MockArgs:
            schema_version = 3
            minimal = False
            output = None

        args = MockArgs()

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            template.run_template(args)
            output = mock_stdout.getvalue()

        assert "version: 3" in output

    def test_run_template_file_output(self):
        """Test run_template with file output."""
        # Mock args object
        class MockArgs:
            schema_version = 2
            minimal = True
            output = "/tmp/test.yml"

        args = MockArgs()

        with patch("builtins.open", mock_open()) as mock_file:
            template.run_template(args)
            mock_file.assert_called_once_with("/tmp/test.yml", 'w')

    def test_run_template_invalid_version(self):
        """Test run_template with invalid schema version."""
        # Mock args object
        class MockArgs:
            schema_version = 99
            minimal = False
            output = None

        args = MockArgs()

        with patch('sys.stderr', new_callable=StringIO):
            with pytest.raises(SystemExit) as exc_info:
                template.run_template(args)
            assert exc_info.value.code == 1

    def test_run_template_file_error(self):
        """Test run_template with file write error."""
        # Mock args object
        class MockArgs:
            schema_version = 3
            minimal = False
            output = "/invalid/path/test.yml"

        args = MockArgs()

        with patch("builtins.open", side_effect=OSError("Permission denied")):
            with patch('sys.stderr', new_callable=StringIO):
                with pytest.raises(SystemExit) as exc_info:
                    template.run_template(args)
                assert exc_info.value.code == 1


class TestSchemaCompatibility:
    """Test compatibility with actual schema definitions."""

    def test_all_schema_versions_generate(self):
        """Test that all schema versions can generate templates."""
        for version in [1, 2, 3]:
            result = template.generate_execution_environment_template(version)
            assert result["version"] == version
            assert isinstance(result, dict)

    def test_v1_schema_fields(self):
        """Test that v1 template contains expected fields."""
        result = template.generate_execution_environment_template(1)

        # Check for v1 specific fields
        if "build_arg_defaults" in result:
            assert "EE_BASE_IMAGE" in result["build_arg_defaults"]
            assert "EE_BUILDER_IMAGE" in result["build_arg_defaults"]

    def test_v2_schema_fields(self):
        """Test that v2 template contains expected fields."""
        result = template.generate_execution_environment_template(2)

        # Check for v2 specific fields
        assert "images" in result
        if "images" in result:
            assert "base_image" in result["images"]

    def test_v3_schema_fields(self):
        """Test that v3 template contains expected fields."""
        result = template.generate_execution_environment_template(3)

        # Check for v3 specific fields
        if "dependencies" in result:
            deps = result["dependencies"]
            # These fields should use the enhanced types in v3
            if "python" in deps:
                # In v3, python can be string or array
                assert isinstance(deps["python"], (str, list))
