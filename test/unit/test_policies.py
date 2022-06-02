from ansible_builder.policies import SignedIdentityType, IgnoreAll, ExactReference


MIRRORED_NAME = 'my-mirror.corp.com:5000/ansible-automation-platform-21/ee-minimal-rhel8:latest'
ORIGINAL_NAME = 'registry.redhat.io/ansible-automation-platform-21/ee-minimal-rhel8:latest'
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
                    ORIGINAL_NAME: [
                        {
                            'type': 'signedBy',
                            'keyType': 'GPGKeys',
                            'keyPath': KEY_PATH,
                            'signedIdentity': {
                                'type': 'exactReference',
                            }
                        }
                    ]
                },
            }
        }
        ref = ExactReference(ORIGINAL_NAME, KEY_PATH)
        assert ref.name == ORIGINAL_NAME
        assert ref.sig_orig_name is None
        assert ref.identity_type == SignedIdentityType.EXACT_REFERENCE
        assert ref.generate_policy() == expected

    def test_init_with_mirroring(self):
        expected = {
            'default': [{'type': 'reject'}],
            'transports': {
                'docker': {
                    MIRRORED_NAME: [
                        {
                            'type': 'signedBy',
                            'keyType': 'GPGKeys',
                            'keyPath': KEY_PATH,
                            'signedIdentity': {
                                'type': 'exactReference',
                                'dockerReference': ORIGINAL_NAME,
                            }
                        }
                    ]
                },
            }
        }
        ref = ExactReference(MIRRORED_NAME, sig_orig_name=ORIGINAL_NAME, keypath=KEY_PATH)
        assert ref.name == MIRRORED_NAME
        assert ref.sig_orig_name == ORIGINAL_NAME
        assert ref.identity_type == SignedIdentityType.EXACT_REFERENCE
        assert ref.generate_policy() == expected
