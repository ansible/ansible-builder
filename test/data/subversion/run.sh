docker image rm exec-env-svn -f
rm -rf examples/bc
ansible-builder build -f examples/subversion/execution-environment.yml --container-runtime=docker -c examples/bc --tag exec-env-svn
ansible-runner --playbook svn.yml run examples/subversion
