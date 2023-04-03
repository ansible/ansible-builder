from ansible_builder import constants
from ansible_builder.containerfile import Containerfile
from ansible_builder.user_definition import UserDefinition


def make_containerfile(tmpdir, ee_path, **cf_kwargs):
    definition = UserDefinition(ee_path)
    build_context = str(tmpdir / '_build')
    c = Containerfile(definition, build_context=build_context, container_runtime='podman', **cf_kwargs)
    return c


def test_insert_custom_steps_list(build_dir_and_ee_yml):
    ee_data = [
        'additional_build_steps:',
        '  prepend:',
        '    - RUN echo This is the custom steps list test',
        '    - RUN whoami',
    ]

    tmpdir, ee_path = build_dir_and_ee_yml("\n".join(ee_data))
    c = make_containerfile(tmpdir, ee_path)
    c._insert_custom_steps("prepend")
    assert c.steps == ['RUN echo This is the custom steps list test', 'RUN whoami']


def test_insert_custom_steps_string(build_dir_and_ee_yml):
    ee_data = [
        'additional_build_steps:',
        '  append: |',
        '    RUN echo This is the custom steps string test',
        '    RUN whoami',
    ]

    tmpdir, ee_path = build_dir_and_ee_yml("\n".join(ee_data))
    c = make_containerfile(tmpdir, ee_path)
    c._insert_custom_steps("append")
    assert c.steps == ['RUN echo This is the custom steps string test', 'RUN whoami']


def test_prepare_galaxy_install_steps(build_dir_and_ee_yml):
    ee_data = [
        'dependencies:',
        '  galaxy: requirements.yml',
    ]
    tmpdir, ee_path = build_dir_and_ee_yml("\n".join(ee_data))
    c = make_containerfile(tmpdir, ee_path)
    c._prepare_galaxy_install_steps()
    expected = [
        f"RUN ansible-galaxy role install $ANSIBLE_GALAXY_CLI_ROLE_OPTS -r {constants.CONTEXT_FILES['galaxy']} --roles-path \"{constants.base_roles_path}\"",
        f"RUN ANSIBLE_GALAXY_DISABLE_GPG_VERIFY=1 ansible-galaxy collection install "
        f"$ANSIBLE_GALAXY_CLI_COLLECTION_OPTS -r {constants.CONTEXT_FILES['galaxy']} --collections-path \"{constants.base_collections_path}\""
    ]
    assert c.steps == expected


def test_prepare_galaxy_install_steps_with_keyring(build_dir_and_ee_yml):
    ee_data = [
        'dependencies:',
        '  galaxy: requirements.yml',
    ]
    tmpdir, ee_path = build_dir_and_ee_yml("\n".join(ee_data))
    c = make_containerfile(tmpdir, ee_path, galaxy_keyring=constants.default_keyring_name)
    c._prepare_galaxy_install_steps()
    expected = [
        f"RUN ansible-galaxy role install $ANSIBLE_GALAXY_CLI_ROLE_OPTS -r {constants.CONTEXT_FILES['galaxy']} --roles-path \"{constants.base_roles_path}\"",
        f"RUN ansible-galaxy collection install $ANSIBLE_GALAXY_CLI_COLLECTION_OPTS -r {constants.CONTEXT_FILES['galaxy']} "
        f"--collections-path \"{constants.base_collections_path}\" --keyring \"{constants.default_keyring_name}\""
    ]
    assert c.steps == expected


def test_prepare_galaxy_install_steps_with_sigcount(build_dir_and_ee_yml):
    sig_count = 3
    ee_data = [
        'dependencies:',
        '  galaxy: requirements.yml',
    ]
    tmpdir, ee_path = build_dir_and_ee_yml("\n".join(ee_data))
    c = make_containerfile(tmpdir, ee_path,
                           galaxy_keyring=constants.default_keyring_name,
                           galaxy_required_valid_signature_count=sig_count)
    c._prepare_galaxy_install_steps()
    expected = [
        f"RUN ansible-galaxy role install $ANSIBLE_GALAXY_CLI_ROLE_OPTS -r {constants.CONTEXT_FILES['galaxy']} --roles-path \"{constants.base_roles_path}\"",
        f"RUN ansible-galaxy collection install $ANSIBLE_GALAXY_CLI_COLLECTION_OPTS -r {constants.CONTEXT_FILES['galaxy']} "
        f"--collections-path \"{constants.base_collections_path}\" --required-valid-signature-count {sig_count} --keyring \"{constants.default_keyring_name}\""
    ]
    assert c.steps == expected


def test_prepare_galaxy_install_steps_with_ignore_code(build_dir_and_ee_yml):
    codes = [1, 2]
    ee_data = [
        'dependencies:',
        '  galaxy: requirements.yml',
    ]
    tmpdir, ee_path = build_dir_and_ee_yml("\n".join(ee_data))
    c = make_containerfile(tmpdir, ee_path,
                           galaxy_keyring=constants.default_keyring_name,
                           galaxy_ignore_signature_status_codes=codes)
    c._prepare_galaxy_install_steps()
    expected = [
        f"RUN ansible-galaxy role install $ANSIBLE_GALAXY_CLI_ROLE_OPTS -r {constants.CONTEXT_FILES['galaxy']} --roles-path \"{constants.base_roles_path}\"",
        f"RUN ansible-galaxy collection install $ANSIBLE_GALAXY_CLI_COLLECTION_OPTS -r {constants.CONTEXT_FILES['galaxy']} "
        f"--collections-path \"{constants.base_collections_path}\" "
        f"--ignore-signature-status-code {codes[0]} --ignore-signature-status-code {codes[1]} "
        f"--keyring \"{constants.default_keyring_name}\""
    ]
    assert c.steps == expected
