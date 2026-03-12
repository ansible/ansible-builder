import json

from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path


class PolicyChoices(Enum):
    """
    Defines the PolicyChoices enumeration for representing different policy options.

    The PolicyChoices enumeration provides three distinct options for managing
    podman container policies. These options determine the behavior related to
    signature handling, verification, and keyring configurations while interacting
    with builder containers. Each option reflects a specific policy strategy
    for dealing with podman's container management processes.

    Attributes:
        SYSTEM (str): Relies on podman's native consumption of system-defined
            policies and signature validation using inline keyring paths without
            any builder-specific overrides.
        IGNORE (str): Configures podman to ignore all signatures by generating
            a policy that bypasses all signature checks.
        SIG_REQ (str): Configures podman to always pull containers (`--pull-always`)
            and utilize a policy that rejects all by default. This policy adds
            identity requirements for referenced builder containers, using an
            explicitly provided keyring and any applicable prefix overrides from
            the Execution Environment (EE) definition.
    """
    SYSTEM = 'system'
    IGNORE = 'ignore_all'
    SIG_REQ = 'signature_required'


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
    """
    Defines an abstract base class for creating and managing podman policy files.

    This class provides an interface to specify the signed identity types and generate
    corresponding policy data, and implements functionality to save the generated policy
    to a file.
    """
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

    def write_policy(self, policy_file):
        '''
        Write the podman policy file.

        :param str policy_file: Path to the policy file.
        '''
        policy_data = self.generate_policy()
        policy_json = json.dumps(policy_data, indent=2)
        path = Path(policy_file)
        path.write_text(policy_json, encoding='utf8')


class RejectAll(BaseImagePolicy):
    """
    Class used to generate a podman image validation policy that rejects any image.
    """
    @property
    def identity_type(self):
        return SignedIdentityType.REJECT_ALL

    def generate_policy(self):
        return {
            'default': [
                {'type': self.identity_type.value}
            ]
        }


class IgnoreAll(BaseImagePolicy):
    """
    Class used to generate a podman image validation policy that accepts any image.
    """

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
    """
    Class used to generate a podman image validation policy using the
    'exactReference' signature identity type.

    Example usage::

        ref = ExactReference('/path/to/keyring.gpg')
        ref.add_image('registry.redhat.io/aap-21/some-image:latest')
        policy_data = ref.generate_policy()
    """

    def __init__(self, keypath):
        '''
        Initializes the ExactReference object.

        :param str keypath: Path to the GPG keyring used to validate all images.
        '''
        # We support only a single key for all images
        self._keypath = keypath
        self._images = []

    @property
    def identity_type(self):
        return SignedIdentityType.EXACT_REFERENCE

    def add_image(self, name, sig_orig_name=None):
        '''
        Add a new image signature name (and optional, original, non-mirrored
        name) for this policy type.

        :param str name: Complete image name to use in the policy file.
        :param str sig_orig_name: If an image is mirrored, this is the complete
            original image name from the location being mirrored.
        '''
        self._images.append((name, sig_orig_name))

    def generate_policy(self):
        images_def = {}

        # Build each image definition
        for name, sig_orig_name in self._images:
            signedIdType = {
                'type': self.identity_type.value
            }
            if sig_orig_name:
                signedIdType['dockerReference'] = sig_orig_name
            else:
                signedIdType['dockerReference'] = name

            definition = {
                'type': 'signedBy',
                'keyType': 'GPGKeys',
                'keyPath': self._keypath,
                'signedIdentity': signedIdType,
            }

            images_def[name] = [definition]

        return {
            'default': [
                {'type': SignedIdentityType.REJECT_ALL.value}
            ],
            'transports': {
                'docker': images_def,
            }
        }
