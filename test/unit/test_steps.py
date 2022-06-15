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
    steps = list(GalaxyInstallSteps("requirements.txt", None, [], None))
    expected = [
        f"RUN ansible-galaxy role install $ANSIBLE_GALAXY_CLI_ROLE_OPTS -r requirements.txt --roles-path \"{constants.base_roles_path}\"",

        f"RUN ANSIBLE_GALAXY_DISABLE_GPG_VERIFY=1 ansible-galaxy collection install "
        f"$ANSIBLE_GALAXY_CLI_COLLECTION_OPTS -r requirements.txt --collections-path \"{constants.base_collections_path}\""
    ]
    assert steps == expected


def test_galaxy_install_steps_with_keyring():
    steps = list(GalaxyInstallSteps("requirements.txt", constants.default_keyring_name, [], None))
    expected = [
        f"RUN ansible-galaxy role install $ANSIBLE_GALAXY_CLI_ROLE_OPTS -r requirements.txt --roles-path \"{constants.base_roles_path}\"",

        f"RUN ansible-galaxy collection install $ANSIBLE_GALAXY_CLI_COLLECTION_OPTS -r requirements.txt "
        f"--collections-path \"{constants.base_collections_path}\" --keyring \"{constants.default_keyring_name}\""
    ]
    assert steps == expected


def test_galaxy_install_steps_with_sig_count():
    sig_count = 3
    steps = list(GalaxyInstallSteps("requirements.txt", constants.default_keyring_name, [], sig_count))
    expected = [
        f"RUN ansible-galaxy role install $ANSIBLE_GALAXY_CLI_ROLE_OPTS -r requirements.txt --roles-path \"{constants.base_roles_path}\"",

        f"RUN ansible-galaxy collection install $ANSIBLE_GALAXY_CLI_COLLECTION_OPTS -r requirements.txt "
        f"--collections-path \"{constants.base_collections_path}\" --required-valid-signature-count {sig_count} "
        f"--keyring \"{constants.default_keyring_name}\""
    ]
    assert steps == expected


def test_galaxy_install_steps_with_ignore_code():
    codes = [1, 2]
    steps = list(GalaxyInstallSteps("requirements.txt", constants.default_keyring_name, codes, None))
    expected = [
        f"RUN ansible-galaxy role install $ANSIBLE_GALAXY_CLI_ROLE_OPTS -r requirements.txt --roles-path \"{constants.base_roles_path}\"",

        f"RUN ansible-galaxy collection install $ANSIBLE_GALAXY_CLI_COLLECTION_OPTS -r requirements.txt "
        f"--collections-path \"{constants.base_collections_path}\" --ignore-signature-status-code {codes[0]} "
        f"--ignore-signature-status-code {codes[1]} --keyring \"{constants.default_keyring_name}\""
    ]
    assert steps == expected
