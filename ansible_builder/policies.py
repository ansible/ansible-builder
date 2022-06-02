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


class SignedIdentityType(Enum):
    """
    Signature identity types as defined in:
    https://github.com/containers/image/blob/main/docs/containers-policy.json.5.md
    """
    REJECT_ALL = 'reject'
    IGNORE_ALL = 'insecureAcceptAnything'
    EXACT_REFERENCE = 'exactReference'
    # NOTE: more types might be supported in the future


class BaseImagePolicy(ABC):

    def __init__(self, name=None, keypath=None):
        self.name = name
        self.keypath = keypath

    @property
    @abstractmethod
    def identity_type(self):
        '''
        Returns the signed identity type enum. Use `value` attribute to get
        the string representation.
        '''

    @abstractmethod
    def generate_policy(self):
        '''
        Generates the podman policy data.

        :returns: A dict representing the policy file data.
        '''


class IgnoreAll(BaseImagePolicy):

    @property
    def identity_type(self):
        return SignedIdentityType.IGNORE_ALL

    def generate_policy(self):
        return {
            'default': [
                {'type': self.identity_type.value}
            ]
        }


class ExactReference(BaseImagePolicy):

    def __init__(self, name, keypath, sig_orig_name=None):
        super().__init__(name=name, keypath=keypath)
        self.sig_orig_name = sig_orig_name

    @property
    def identity_type(self):
        return SignedIdentityType.EXACT_REFERENCE

    def generate_policy(self):
        signedIdType = {
            'type': self.identity_type.value
        }
        if self.sig_orig_name:
            signedIdType['dockerReference'] = self.sig_orig_name

        return {
            'default': [
                {'type': SignedIdentityType.REJECT_ALL.value}
            ],
            'transports': {
                'docker': {
                    self.name: [
                        {
                            'type': 'signedBy',
                            'keyType': 'GPGKeys',
                            'keyPath': self.keypath,
                            'signedIdentity': signedIdType,
                        }
                    ]
                },
            }
        }
