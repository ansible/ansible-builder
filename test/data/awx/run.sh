docker image rm exec-env-ansible-venv -f
rm -rf examples/bc
ansible-builder build -f examples/awx/execution-environment.yml --container-runtime=docker -c examples/bc --tag exec-env-ansible-venv
ansible-runner --playbook test.yml run examples/awx -vvv
