#!/usr/bin/env bash

if [ ! $1 ]
then
  echo "Provide an argument which is the name of a subfolder"
  return 1 2>/dev/null
  exit 1
fi

echo "Running example $1"

IMAGE_NAME=exec-env-$1

docker image rm $IMAGE_NAME -f
rm -rf examples/bc
ansible-builder build -f examples/$1/execution-environment.yml --container-runtime=docker -c examples/bc --tag $IMAGE_NAME
ansible-runner --playbook $1.yml run examples/$1 -v
