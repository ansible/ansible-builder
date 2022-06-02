from ansible_builder.policies import SignedIdentityType, IgnoreAll, ExactReference


MIRRORED_NAME_1 = 'my-mirror.corp.com:5000/ansible-automation-platform-21/ee-minimal-rhel8:latest'
ORIGINAL_NAME_1 = 'registry.redhat.io/ansible-automation-platform-21/ee-minimal-rhel8:latest'
MIRRORED_NAME_2 = 'my-mirror.corp.com:5000/ubuntu/funny-name:latest'
ORIGINAL_NAME_2 = 'registry.ubuntu.com/funny-name:latest'
KEY_PATH = '/some/path/to/keyring.gpg'


class TestIgnoreAll:

    def test_init(self):
        expected = {'default': [{'type': 'insecureAcceptAnything'}]}
        ref = IgnoreAll()
        assert ref.identity_type == SignedIdentityType.IGNORE_ALL
        assert ref.generate_policy() == expected


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
