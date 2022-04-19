import os
import pytest

from ansible_builder.exceptions import DefinitionError
from ansible_builder.main import AnsibleBuilder
from ansible_builder.user_definition import UserDefinition


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
            "Expected 'additional_build_steps' in the provided definition file to be a dictionary\n"
            "with keys 'prepend' and/or 'append'; found a str instead."
        ),  # not right format for additional_build_steps
        (
            "{'version': 1, 'additional_build_steps': {'middle': 'RUN me'}}",
            "Keys ('middle',) are not allowed in 'additional_build_steps'."
        ),  # there are no "middle" build steps
        (
            "{'version': 1, 'build_arg_defaults': {'EE_BASE_IMAGE': ['foo']}}",
            "Expected build_arg_defaults.EE_BASE_IMAGE to be a string; Found a <class 'list'> instead."
        ),  # image itself is wrong type
        (
            "{'version': 1, 'build_arg_defaults': {'BUILD_ARRRRRG': 'swashbuckler'}}",
            "Keys {'BUILD_ARRRRRG'} are not allowed in 'build_arg_defaults'."
        ),  # image itself is wrong type
        (
            "{'version': 1, 'ansible_config': ['ansible.cfg']}",
            "Expected 'ansible_config' in the provided definition file to\n"
            "be a string; found a list instead."
        ),
        (
            "{'version': 1, 'foo': 'bar'}",
            "Error: Unknown yaml key(s), {'foo'}, found in the definition file."
        ),
    ], ids=[
        'integer', 'missing_file', 'additional_steps_format', 'additional_unknown',
        'build_args_value_type', 'unexpected_build_arg', 'config_type', 'unknown_key'
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
        path = exec_env_definition_file("{'bad_key': 1}")
        with pytest.raises(DefinitionError) as error:
            AnsibleBuilder(filename=path)
        assert "Error: Unknown yaml key(s), {'bad_key'}, found in the definition file." in str(error.value.args[0])
