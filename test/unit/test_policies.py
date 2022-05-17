from ansible_builder.policies import IdentityType, RejectAll, ExactReference


MIRRORED_NAME = 'my-mirror.corp.com:5000/ansible-automation-platform-21/ee-minimal-rhel8:latest'
ORIGINAL_NAME = 'registry.redhat.io/ansible-automation-platform-21/ee-minimal-rhel8:latest'


class TestRejectAll:

    def test_init(self):
        expected = {'default': [{'type': IdentityType.REJECT_ALL}]}
        ref = RejectAll()
        assert ref.identity_type == IdentityType.REJECT_ALL
        assert ref.generate_policy() == expected


class TestExactReference:

    def test_init(self):
        ref = ExactReference(MIRRORED_NAME)
        assert ref.name == MIRRORED_NAME
        assert ref.sig_orig_name is None
        assert ref.identity_type == IdentityType.EXACT_REFERENCE

    def test_init_with_orig_name(self):
        ref = ExactReference(MIRRORED_NAME, ORIGINAL_NAME)
        assert ref.name == MIRRORED_NAME
        assert ref.sig_orig_name == ORIGINAL_NAME
        assert ref.identity_type == IdentityType.EXACT_REFERENCE
