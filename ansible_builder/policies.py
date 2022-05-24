from abc import ABC, abstractmethod
from enum import Enum


class PolicyChoices(Enum):
    # SYSTEM: relies on podman's consumption of system policy/signature with
    # inline keyring paths, no builder-specific overrides are possible
    SYSTEM = 'system'

    # IGNORE: run podman with generated policy that ignores all signatures
    IGNORE = 'ignore_all'

    # SIG_REQ: run podman with `--pull-always` and generated policy that rejects
    # all by default, with generated identity requirements for referenced builder
    # containers using explicitly-provided keyring and any prefix overrides from
    # EE definition as necessary.
    SIG_REQ = 'signature_required'

    # CUSTOM: run podman with `--pull-always` and a user-supplied policy file
    # from --container-policy-file, no additional keyring or match overrides are
    # possible.
    CUSTOM = 'custom_policy'


class IdentityType(Enum):
    """
    Signature identity types as defined in:
    https://github.com/containers/image/blob/main/docs/containers-policy.json.5.md
    """
    REJECT_ALL = 'reject'
    EXACT_REFERENCE = 'exactReference'
    # NOTE: more types might be supported in the future


class BaseImagePolicy(ABC):

    def __init__(self, name=None):
        self.name = name

    @property
    @abstractmethod
    def identity_type(self):
        pass

    @abstractmethod
    def generate_policy(self):
        pass


class RejectAll(BaseImagePolicy):

    @property
    def identity_type(self):
        return IdentityType.REJECT_ALL

    def generate_policy(self):
        return {
            'default': [
                {'type': self.identity_type}
            ]
        }


class ExactReference(BaseImagePolicy):

    def __init__(self, name, sig_orig_name=None):
        super().__init__(name)
        self.sig_orig_name = sig_orig_name

    @property
    def identity_type(self):
        return IdentityType.EXACT_REFERENCE

    def generate_policy(self):
        return {
            'default': [
                {'type': IdentityType.REJECT_ALL}
            ],
            'transports': {
                'docker': {},
            }
        }
