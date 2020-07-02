default_file = 'execution-environment.yml'
default_base_image = 'shanemcd/ansible-runner'
default_tag = 'ansible-execution-env:latest'
default_build_context = 'context'
runtime_files={
    'podman': 'Containerfile',
    'docker': 'Dockerfile'
}
default_container_runtime = 'podman'
