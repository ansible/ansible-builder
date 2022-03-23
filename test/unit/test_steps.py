import pytest
import textwrap

from ansible_builder import constants
from ansible_builder.steps import AdditionalBuildSteps, GalaxyInstallSteps


@pytest.mark.parametrize('verb', ['prepend', 'append'])
def test_additional_build_steps(verb):
    additional_build_steps = {
        'prepend': ["RUN echo This is the prepend test", "RUN whoami"],
        'append': textwrap.dedent("""
        RUN echo This is the append test
        RUN whoami
        """)
    }
    steps = AdditionalBuildSteps(additional_build_steps[verb])

    assert len(list(steps)) == 2

def test_galaxy_install_steps():
    steps = list(GalaxyInstallSteps("requirements.txt", None))
    expected = [
        f"RUN ansible-galaxy role install -r requirements.txt --roles-path {constants.base_roles_path}",
        f"RUN ANSIBLE_GALAXY_DISABLE_GPG_VERIFY=1 ansible-galaxy collection install $ANSIBLE_GALAXY_CLI_COLLECTION_OPTS -r requirements.txt --collections-path {constants.base_collections_path}"
    ]
    assert steps == expected

def test_galaxy_install_steps_with_keyring():
    steps = list(GalaxyInstallSteps("requirements.txt", "mykeyring.gpg"))
    expected = [
        f"RUN ansible-galaxy role install -r requirements.txt --roles-path {constants.base_roles_path}",
        f"RUN ansible-galaxy collection install $ANSIBLE_GALAXY_CLI_COLLECTION_OPTS -r requirements.txt --collections-path {constants.base_collections_path} --keyring ./keyring.gpg"
    ]
    assert steps == expected
