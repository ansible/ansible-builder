from abc import ABC, abstractmethod
from enum import Enum


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
                'atomic': {}
            }
        }
