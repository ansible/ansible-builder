docker image rm exec-env-pip -f
rm -rf examples/bc
ansible-builder build -f examples/pip/execution-environment.yml --container-runtime=docker -c examples/bc --tag exec-env-pip
ansible-runner --playbook pip_bottle.yml run examples/pip -vvv
