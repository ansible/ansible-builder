import json
from pathlib import Path

from ansible_builder import constants
from ansible_builder.policies import SignedIdentityType, RejectAll, IgnoreAll, ExactReference


MIRRORED_NAME_1 = 'my-mirror.corp.com:5000/ansible-automation-platform-21/ee-minimal-rhel8:latest'
ORIGINAL_NAME_1 = 'registry.redhat.io/ansible-automation-platform-21/ee-minimal-rhel8:latest'
MIRRORED_NAME_2 = 'my-mirror.corp.com:5000/ubuntu/funny-name:latest'
ORIGINAL_NAME_2 = 'registry.ubuntu.com/funny-name:latest'
KEY_PATH = '/some/path/to/keyring.gpg'


class TestRejectAll:

    def test_init(self):
        expected = {'default': [{'type': 'reject'}]}
        ref = RejectAll()
        assert ref.identity_type == SignedIdentityType.REJECT_ALL
        assert ref.generate_policy() == expected

    def test_write_policy(self, tmp_path):
        ''' Test write_policy() writes a JSON file with correct data. '''
        expected = {'default': [{'type': 'reject'}]}
        policy_file = str(tmp_path / constants.default_policy_file_name)
        ref = RejectAll()
        ref.write_policy(policy_file)
        output = Path(policy_file)
        assert output.exists()
        assert output.is_file()
        assert expected == json.loads(output.read_text(encoding='utf8'))


class TestIgnoreAll:

    def test_init(self):
        expected = {'default': [{'type': 'insecureAcceptAnything'}]}
        ref = IgnoreAll()
        assert ref.identity_type == SignedIdentityType.IGNORE_ALL
        assert ref.generate_policy() == expected

    def test_write_policy(self, tmp_path):
        ''' Test write_policy() writes a JSON file with correct data. '''
        expected = {'default': [{'type': 'insecureAcceptAnything'}]}
        policy_file = str(tmp_path / constants.default_policy_file_name)
        ref = IgnoreAll()
        ref.write_policy(policy_file)
        output = Path(policy_file)
        assert output.exists()
        assert output.is_file()
        assert expected == json.loads(output.read_text(encoding='utf8'))


class TestExactReference:

    def test_init(self):
        expected = {
            'default': [{'type': 'reject'}],
            'transports': {
                'docker': {
                    ORIGINAL_NAME_1: [
                        {
                            'type': 'signedBy',
                            'keyType': 'GPGKeys',
                            'keyPath': KEY_PATH,
                            'signedIdentity': {
                                'type': 'exactReference',
                                'dockerReference': ORIGINAL_NAME_1,
                            }
                        }
                    ],
                    ORIGINAL_NAME_2: [
                        {
                            'type': 'signedBy',
                            'keyType': 'GPGKeys',
                            'keyPath': KEY_PATH,
                            'signedIdentity': {
                                'type': 'exactReference',
                                'dockerReference': ORIGINAL_NAME_2,
                            }
                        }
                    ],
                },
            }
        }
        ref = ExactReference(KEY_PATH)
        ref.add_image(ORIGINAL_NAME_1)
        ref.add_image(ORIGINAL_NAME_2)
        assert ref.identity_type == SignedIdentityType.EXACT_REFERENCE
        assert ref.generate_policy() == expected

    def test_init_with_mirroring(self):
        expected = {
            'default': [{'type': 'reject'}],
            'transports': {
                'docker': {
                    MIRRORED_NAME_1: [
                        {
                            'type': 'signedBy',
                            'keyType': 'GPGKeys',
                            'keyPath': KEY_PATH,
                            'signedIdentity': {
                                'type': 'exactReference',
                                'dockerReference': ORIGINAL_NAME_1,
                            }
                        }
                    ],
                    MIRRORED_NAME_2: [
                        {
                            'type': 'signedBy',
                            'keyType': 'GPGKeys',
                            'keyPath': KEY_PATH,
                            'signedIdentity': {
                                'type': 'exactReference',
                                'dockerReference': ORIGINAL_NAME_2,
                            }
                        }
                    ]

                },
            }
        }
        ref = ExactReference(KEY_PATH)
        ref.add_image(MIRRORED_NAME_1, ORIGINAL_NAME_1)
        ref.add_image(MIRRORED_NAME_2, ORIGINAL_NAME_2)
        assert ref.identity_type == SignedIdentityType.EXACT_REFERENCE
        assert ref.generate_policy() == expected

    def test_write_policy(self, tmp_path):
        ''' Test write_policy() writes a JSON file with correct data. '''
        expected = {
            'default': [{'type': 'reject'}],
            'transports': {
                'docker': {
                    ORIGINAL_NAME_1: [
                        {
                            'type': 'signedBy',
                            'keyType': 'GPGKeys',
                            'keyPath': KEY_PATH,
                            'signedIdentity': {
                                'type': 'exactReference',
                                'dockerReference': ORIGINAL_NAME_1,
                            }
                        }
                    ],
                },
            }
        }

        policy_file = str(tmp_path / constants.default_policy_file_name)
        ref = ExactReference(KEY_PATH)
        ref.add_image(ORIGINAL_NAME_1)
        ref.write_policy(policy_file)
        output = Path(policy_file)
        assert output.exists()
        assert output.is_file()
        assert expected == json.loads(output.read_text(encoding='utf8'))
