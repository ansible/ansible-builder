import shutil

default_file = 'execution-environment.yml'
default_tag = 'ansible-execution-env:latest'
default_build_context = 'context'
default_verbosity = 2
runtime_files = {
    'podman': 'Containerfile',
    'docker': 'Dockerfile'
}
default_container_runtime = 'podman'
base_roles_path = '/usr/share/ansible/roles'
base_collections_path = '/usr/share/ansible/collections'

build_arg_defaults = dict(
    # empty string values here still allow the build arg to be emitted into the generated Containerfile
    ANSIBLE_GALAXY_CLI_COLLECTION_OPTS='',
    ANSIBLE_GALAXY_CLI_ROLE_OPTS='',
    EE_BASE_IMAGE='quay.io/ansible/ansible-runner:latest',
    # this value is removed elsewhere for v3+ schemas
    EE_BUILDER_IMAGE='quay.io/ansible/ansible-builder:latest',
    PKGMGR_PRESERVE_CACHE='',
)

user_content_subfolder = '_build'

if shutil.which('podman'):
    default_container_runtime = 'podman'
else:
    default_container_runtime = 'docker'

default_keyring_name = 'keyring.gpg'
default_policy_file_name = 'policy.json'

# Files that need to be moved into the build context, and their naming inside the context
CONTEXT_FILES = {
    # HACK: hacking in prototype other kinds of deps for dynamic builder
    'python_interpreter': '',
    'ansible_core': '',
    'ansible_runner': '',

    'galaxy': 'requirements.yml',
    'python': 'requirements.txt',
    'system': 'bindep.txt',
}

FINAL_IMAGE_BIN_PATH = "/opt/builder/bin"
