docker image rm exec-env-at -f
rm -rf examples/bc
ansible-builder build -f examples/ansible.posix.at/execution-environment.yml --container-runtime=docker -c examples/bc --tag exec-env-at
ansible-runner --playbook at.yml run examples/ansible.posix.at -vvv
