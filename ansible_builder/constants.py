import shutil

default_file = 'execution-environment.yml'
default_tag = 'ansible-execution-env:latest'
default_build_context = 'context'
default_verbosity = 2
runtime_files={
    'podman': 'Containerfile',
    'docker': 'Dockerfile'
}
default_container_runtime = 'podman'
base_roles_path = '/usr/share/ansible/roles'
base_collections_path = '/usr/share/ansible/collections'

build_arg_defaults = dict(
    ANSIBLE_GALAXY_CLI_COLLECTION_OPTS='',
    ANSIBLE_RUNNER_IMAGE='quay.io/ansible/ansible-runner:devel',
    PYTHON_BUILDER_IMAGE='quay.io/ansible/python-builder:latest'
)

user_content_subfolder = '_build'

if shutil.which('podman'):
    default_container_runtime = 'podman'
else:
    default_container_runtime = 'docker'
