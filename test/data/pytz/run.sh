docker image rm ansible-execution-env -f
rm -rf examples/bc
ansible-builder build -f examples/pytz/execution-environment.yml --container-runtime=docker -c examples/bc
# docker run --rm --tty --interactive --mount "type=bind,src=$(pwd)/examples/pytz,dst=/alan" --env ANSIBLE_STDOUT_CALLBACK=default -e ANSIBLE_CALLBACK_PLUGINS="" ansible-execution-env ansible-playbook -i localhost, /alan/rrule_test.yml
ansible-runner --playbook rrule_test.yml run examples/pytz
