import os
import pytest

from ansible_builder import constants
from ansible_builder.exceptions import DefinitionError
from ansible_builder.main import AnsibleBuilder
from ansible_builder.user_definition import UserDefinition, ImageDescription


class TestUserDefinition:

    def test_definition_syntax_error(self, data_dir):
        path = os.path.join(data_dir, 'definition_files/bad.yml')

        with pytest.raises(DefinitionError) as error:
            AnsibleBuilder(action='create', filename=path)

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
        (
            "{'version': 3, 'additional_build_steps': {'prepend': ''}}",
            "Additional properties are not allowed ('prepend' was unexpected)"
        ),  # 'prepend' is renamed in v2
        (
            "{'version': 3, 'images': { 'base_image': {'name': 'base_image:latest'}}, "
            "'additional_build_files': [ {'src': 'a', 'dest': '../b'} ]}",
            "'dest' must not be an absolute path or contain '..': ../b"
        ),  # destination cannot contain ..
        (
            "{'version': 3, 'images': { 'base_image': {'name': 'base_image:latest'}}, "
            "'additional_build_files': [ {'src': 'a', 'dest': '/b'} ]}",
            "'dest' must not be an absolute path or contain '..': /b"
        ),  # destination cannot be absolute
        (
            "{'version': 3, 'additional_build_files': [ {'dest': 'b'} ]}",
            "'src' is a required property"
        ),  # source is required
        (
            "{'version': 3, 'additional_build_files': [ {'src': 'a'} ]}",
            "'dest' is a required property"
        ),  # destination is required
        (
            "{'version': 3, 'ansible_config': 'ansible.cfg' }",
            "Additional properties are not allowed ('ansible_config' was unexpected)"
        ),  # ansible_config not supported in v3
        (
            "{'version': 3, 'images': { 'base_image': {'name': 'base_image:latest'}, "
            "'builder_image': {'name': 'builder_image:latest'} }}",
            "Additional properties are not allowed ('builder_image' was unexpected)"
        ),  # builder_image not suppored in v3
        (
            "{'version': 3, 'options': { 'skip_ansible_check': 'True' } }",
            "'True' is not of type 'boolean'"
        ),
    ], ids=[
        'integer', 'missing_file', 'additional_steps_format', 'additional_unknown',
        'build_args_value_type', 'unexpected_build_arg', 'config_type', 'v1_contains_v2_key',
        'v2_unknown_key', 'v1_base_image_in_v2', 'v1_builder_image_in_v2', 'prepend_in_v3',
        'dest_has_dot_dot', 'dest_is_absolute', 'src_req', 'dest_req', 'ansible_cfg',
        'builder_in_v3', 'opt_skip_ans_chk',
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
            AnsibleBuilder(action='create', filename=path)

        err_msg = "Could not detect 'exec_env.txt' file in this directory.\nUse -f to specify a different location."
        assert err_msg in str(error.value.args[0])

    def test_ee_validated_early(self, exec_env_definition_file):
        """
        Expect the EE file to be validated early during AnsibleBuilder instantiation.
        """
        path = exec_env_definition_file("{'version': 1, 'bad_key': 1}")
        with pytest.raises(DefinitionError) as error:
            AnsibleBuilder(action='create', filename=path)
        assert "Additional properties are not allowed ('bad_key' was unexpected)" in str(error.value.args[0])

    def test_ee_missing_image_name(self, exec_env_definition_file):
        path = exec_env_definition_file("{'version': 2, 'images': { 'base_image': {'signature_original_name': ''}}}")
        with pytest.raises(DefinitionError) as error:
            AnsibleBuilder(action='create', filename=path)
        assert "'name' is a required field for 'base_image'" in str(error.value.args[0])

    def test_v1_to_v2_key_upgrades(self, exec_env_definition_file):
        """ Test that EE schema keys are upgraded from version V1 to V2. """
        path = exec_env_definition_file(
            "{'version': 1, 'additional_build_steps': {'prepend': 'value1', 'append': 'value2'}}"
        )
        definition = UserDefinition(path)
        definition.validate()
        add_bld_steps = definition.raw['additional_build_steps']
        assert 'prepend' in add_bld_steps
        assert 'append' in add_bld_steps
        assert add_bld_steps['prepend'] == 'value1'
        assert add_bld_steps['append'] == 'value2'
        assert 'prepend_final' in add_bld_steps
        assert 'append_final' in add_bld_steps
        assert add_bld_steps['prepend_final'] == add_bld_steps['prepend']
        assert add_bld_steps['append_final'] == add_bld_steps['append']

    def test_v2_images(self, exec_env_definition_file):
        """
        Verify that image definition contents are assigned correctly and copied
        to the build_arg_defaults equivalents.
        """
        path = exec_env_definition_file(
            "{'version': 2, 'images': { 'base_image': {'name': 'base_image:latest'}, "
            "'builder_image': {'name': 'builder_image:latest'} }}"
        )
        definition = UserDefinition(path)
        definition.validate()

        assert definition.base_image.name == "base_image:latest"
        assert definition.builder_image.name == "builder_image:latest"
        assert definition.build_arg_defaults['EE_BASE_IMAGE'] == "base_image:latest"
        assert definition.build_arg_defaults['EE_BUILDER_IMAGE'] == "builder_image:latest"

    def test_v3_ansible_install_refs(self, exec_env_definition_file):
        path = exec_env_definition_file(
            """
            {'version': 3,
             'images': { 'base_image': {'name': 'base_image:latest'}},
             'dependencies': {
                'ansible_core': {'package_pip': 'ansible-core==2.13'},
                'ansible_runner': { 'package_pip': 'ansible-runner==2.3.1'}
             }
            }
            """
        )
        definition = UserDefinition(path)
        definition.validate()
        assert definition.ansible_core_ref == "ansible-core==2.13"
        assert definition.ansible_runner_ref == "ansible-runner==2.3.1"
        assert definition.ansible_ref_install_list == "ansible-core==2.13 ansible-runner==2.3.1"

    def test_v3_inline_python(self, exec_env_definition_file):
        """
        Test that inline values for dependencies.python work.
        """
        path = exec_env_definition_file(
            "{'version': 3, 'images': { 'base_image': {'name': 'base_image:latest'}},"
            "'dependencies': {'python': ['req1', 'req2']}}"
        )
        definition = UserDefinition(path)
        definition.validate()

        python_req = definition.raw.get('dependencies', {}).get('python')
        assert python_req == ['req1', 'req2']

    def test_v3_inline_system(self, exec_env_definition_file):
        """
        Test that inline values for dependencies.system work.
        """
        path = exec_env_definition_file(
            "{'version': 3, 'images': { 'base_image': {'name': 'base_image:latest'}},"
            "'dependencies': {'system': ['req1', 'req2']}}"
        )
        definition = UserDefinition(path)
        definition.validate()

        system_req = definition.raw.get('dependencies', {}).get('system')
        assert system_req == ['req1', 'req2']

    def test_v3_skip_ansible_check_default(self, exec_env_definition_file):
        """
        Test that options.skip_ansible_check defaults to False
        """
        path = exec_env_definition_file(
            "{'version': 3, 'images': { 'base_image': {'name': 'base_image:latest'}}}"
        )
        definition = UserDefinition(path)
        definition.validate()

        value = definition.raw.get('options', {}).get('skip_ansible_check')
        assert value is False

    def test_v3_user_id(self, exec_env_definition_file):
        """
        Test that options.user defaults to 1000
        """
        path = exec_env_definition_file(
            "{'version': 3, 'images': { 'base_image': {'name': 'base_image:latest'}}}"
        )
        definition = UserDefinition(path)
        definition.validate()

        value = definition.raw.get('options', {}).get('user')
        assert value == '1000'

    def test_v3_set_user_name(self, exec_env_definition_file):
        """
        Test that options.user sets to username
        """
        path = exec_env_definition_file(
            "{'version': 3, 'images': { 'base_image': {'name': 'base_image:latest'}},"
            "'options': {'user': 'bob'}}"
        )
        definition = UserDefinition(path)
        definition.validate()

        value = definition.raw.get('options', {}).get('user')
        assert value == 'bob'

    def test_v3_set_tags(self, exec_env_definition_file):
        """
        Test that options.tags sets to tags
        """
        path = exec_env_definition_file(
            "{'version': 3, 'images': { 'base_image': {'name': 'base_image:latest'}}, "
            "'options': {'tags': ['ee_test:latest']}}"
        )
        definition = UserDefinition(path)
        definition.validate()

        value = definition.raw.get('options', {}).get('tags')
        assert value == ['ee_test:latest']

    def test_v3_dependencies_property(self, exec_env_definition_file):
        deps = {
            'python': ['req1', 'req2'],
            'system': ['sysreq1', 'sysreq2'],
            'exclude': {
                'all_from_collections': ['a.b', 'c.d'],
            }
        }

        ee_content = {
            'version': 3,
            'dependencies': deps,
        }

        path = exec_env_definition_file(content=ee_content)
        definition = UserDefinition(path)
        definition.validate()

        value = definition.dependencies
        assert value == deps


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


class TestDefaultEEFilename:
    """
    Class to handle test setup/teardown of tests that need to change working
    directory to test the default EE filename in the current directory.
    """

    def setup_method(self):
        self._old_workdir = os.getcwd()  # pylint: disable=W0201

    def teardown_method(self):
        os.chdir(self._old_workdir)

    def test_all_default_filenames(self, tmp_path):
        """
        Test finding all variations of the default execution environment filename.
        """
        os.chdir(str(tmp_path))
        for ext in constants.YAML_FILENAME_EXTENSIONS:
            ee = tmp_path / f"{constants.DEFAULT_EE_BASENAME}.{ext}"
            ee.write_text("version: 3")
            UserDefinition()   # This would fail if the file is not found
            ee.unlink()

    def test_missing_default_file(self, tmp_path):
        """
        Test that we fail if the default file is not found.
        """
        os.chdir(str(tmp_path))
        with pytest.raises(DefinitionError, match="Default execution environment file not found in current directory."):
            UserDefinition()
