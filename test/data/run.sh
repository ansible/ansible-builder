#!/usr/bin/env bash

run_example () {
  echo ""
  echo "Running Example: $1"
  IMAGE_NAME=exec-env-$1
  docker image rm $IMAGE_NAME -f
  rm -rf bc
  echo ""
  echo "Running:"
  echo "ansible-builder build -f $1/execution-environment.yml --container-runtime=docker -c bc --tag $IMAGE_NAME"
  ansible-builder build -f $1/execution-environment.yml --container-runtime=docker -c bc --tag $IMAGE_NAME
  echo ""
  echo "Running:"
  echo "ansible-runner run --playbook $1.yml $1 -v"
  ansible-runner run --playbook $1.yml $1 -v
  return 0
}

cd test/data

if [ ! $1 ]
then
  for dir in */;
  do
      if [ $dir != "bc/" ]; then
        run_example ${dir%*/}
      fi
  done
else
  run_example $1
fi

cd ..
