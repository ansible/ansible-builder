import shutil

default_file = 'execution-environment.yml'
default_base_image = 'quay.io/ansible/ansible-runner:devel'
default_tag = 'ansible-execution-env:latest'
default_build_context = 'context'
runtime_files={
    'podman': 'Containerfile',
    'docker': 'Dockerfile'
}
default_container_runtime = 'podman'
base_roles_path = '/usr/share/ansible/roles'
base_collections_path = '/usr/share/ansible/collections'

if shutil.which('podman'):
    default_container_runtime = 'podman'
else:
    default_container_runtime = 'docker'
