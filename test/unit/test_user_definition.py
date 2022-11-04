import os
import pytest

from ansible_builder.exceptions import DefinitionError
from ansible_builder.main import AnsibleBuilder
from ansible_builder.user_definition import UserDefinition, ImageDescription


class TestUserDefinition:

    def test_definition_syntax_error(self, data_dir):
        path = os.path.join(data_dir, 'definition_files/bad.yml')

        with pytest.raises(DefinitionError) as error:
            AnsibleBuilder(filename=path)

        assert 'An error occurred while parsing the definition file:' in str(error.value.args[0])

    @pytest.mark.parametrize('yaml_text,expect', [
        ('1', 'Definition must be a dictionary, not int'),  # integer
        (
            "{'version': 1, 'dependencies': {'python': 'foo/not-exists.yml'}}",
            'not-exists.yml does not exist'
        ),  # missing file
        (
            "{'version': 1, 'additional_build_steps': 'RUN me'}",
            "'RUN me' is not of type 'object'"
        ),  # not right format for additional_build_steps
        (
            "{'version': 1, 'additional_build_steps': {'middle': 'RUN me'}}",
            "Additional properties are not allowed ('middle' was unexpected)"
        ),  # there are no "middle" build steps
        (
            "{'version': 1, 'build_arg_defaults': {'EE_BASE_IMAGE': ['foo']}}",
            "['foo'] is not of type 'string'"
        ),  # image itself is wrong type
        (
            "{'version': 1, 'build_arg_defaults': {'BUILD_ARRRRRG': 'swashbuckler'}}",
            "Additional properties are not allowed ('BUILD_ARRRRRG' was unexpected)"
        ),  # image itself is wrong type
        (
            "{'version': 1, 'ansible_config': ['ansible.cfg']}",
            "['ansible.cfg'] is not of type 'string'"
        ),
        (
            "{'version': 1, 'images': 'bar'}",
            "Additional properties are not allowed ('images' was unexpected)"
        ),
        (
            "{'version': 2, 'foo': 'bar'}",
            "Additional properties are not allowed ('foo' was unexpected)"
        ),
        (
            "{'version': 2, 'build_arg_defaults': {'EE_BASE_IMAGE': 'foo'}, 'images': {}}",
            "Additional properties are not allowed ('EE_BASE_IMAGE' was unexpected)"
        ),  # v1 base image defined in v2 file
        (
            "{'version': 2, 'build_arg_defaults': {'EE_BUILDER_IMAGE': 'foo'}, 'images': {}}",
            "Additional properties are not allowed ('EE_BUILDER_IMAGE' was unexpected)"
        ),  # v1 builder image defined in v2 file
    ], ids=[
        'integer', 'missing_file', 'additional_steps_format', 'additional_unknown',
        'build_args_value_type', 'unexpected_build_arg', 'config_type', 'v1_contains_v2_key',
        'v2_unknown_key', 'v1_base_image_in_v2', 'v1_builder_image_in_v2'
    ])
    def test_yaml_error(self, exec_env_definition_file, yaml_text, expect):
        path = exec_env_definition_file(yaml_text)
        with pytest.raises(DefinitionError) as exc:
            definition = UserDefinition(path)
            definition.validate()
        if expect:
            assert expect in exc.value.args[0]

    def test_file_not_found_error(self):
        path = "exec_env.txt"

        with pytest.raises(DefinitionError) as error:
            AnsibleBuilder(filename=path)

        assert "Could not detect 'exec_env.txt' file in this directory.\nUse -f to specify a different location." in str(error.value.args[0])

    def test_ee_validated_early(self, exec_env_definition_file):
        """
        Expect the EE file to be validated early during AnsibleBuilder instantiation.
        """
        path = exec_env_definition_file("{'version': 1, 'bad_key': 1}")
        with pytest.raises(DefinitionError) as error:
            AnsibleBuilder(filename=path)
        assert "Additional properties are not allowed ('bad_key' was unexpected)" in str(error.value.args[0])

    def test_ee_missing_image_name(self, exec_env_definition_file):
        path = exec_env_definition_file("{'version': 2, 'images': { 'base_image': {'signature_original_name': ''}}}")
        with pytest.raises(DefinitionError) as error:
            AnsibleBuilder(filename=path)
        assert "'name' is a required field for 'base_image'" in str(error.value.args[0])


class TestImageDescription:

    def test_bad_programmer(self):
        with pytest.raises(ValueError) as error:
            ImageDescription({}, 'invalid_image_key')
        assert "Invalid image key used for initialization: invalid_image_key" in str(error)

    @pytest.mark.parametrize('key', ['base_image', 'builder_image'])
    def test_missing_name(self, key):
        ee_section = {key: {'signature_original_name': ''}}
        with pytest.raises(DefinitionError) as error:
            ImageDescription(ee_section, key)
        assert f"'name' is a required field for '{key}'" in str(error.value.args[0])

    @pytest.mark.parametrize('key', ['base_image', 'builder_image'])
    @pytest.mark.parametrize('image', ['registry.redhat.io/ansible-automation-platform-21/ee-minimal-rhel8',
                                       'registry.redhat.io/ansible-automation-platform-21/ee-minimal-rhel8:'
                                       ])
    def test_missing_name_tag(self, key, image):
        """
        Test that image.name fails when it doesn't have a tag.
        """
        ee_section = {key: {'name': image}}
        with pytest.raises(DefinitionError) as error:
            ImageDescription(ee_section, key)
        assert f"Container image requires a tag: {image}" in str(error.value.args[0])

    @pytest.mark.parametrize('key', ['base_image', 'builder_image'])
    @pytest.mark.parametrize('image', ['registry.redhat.io/ansible-automation-platform-21/ee-minimal-rhel8',
                                       'registry.redhat.io/ansible-automation-platform-21/ee-minimal-rhel8:'
                                       ])
    def test_missing_orig_name_tag(self, key, image):
        """
        Test that image.signature_original_name fails when it doesn't have a tag.
        """
        ee_section = {key: {'name': 'my-mirror/aap/ee:latest', 'signature_original_name': image}}
        with pytest.raises(DefinitionError) as error:
            ImageDescription(ee_section, key)
        assert f"Container image requires a tag: {image}" in str(error.value.args[0])
