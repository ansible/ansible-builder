## Test Inputs and Examples

This folder contains execution environment definitions for purposes of integration testing and demonstration.
These instructions will use the `pytz` case, but similar commands will work for other examples.
This example demonstrates the use of a collection's python dependency.

### Build Manually

Run the example:

```
ansible-builder build \
  -f test/data/pytz/execution-environment.yml \
  -c my_new_bc \
  -t my_new_tag
```

After it successfully completes, you should see that `my_new_tag` is listed in `podman images`.
If you want to use docker as opposed to podman, the runtime must be specified:

```
ansible-builder build \
  -f test/data/pytz/execution-environment.yml \
  -c my_new_bc \
  -t my_new_tag \
  --container-runtime docker
```

### Helper Script with ansible-runner

You can build and use the image inside of `ansible-runner` by invoking the `run.sh` script.

```
source test/data/run.sh pytz
```

This produces an image called `exec-env-pytz`. The steps it follows are:

 - deletes the existing build context and image.
 - creates a new build context and image with `ansible-builder build`.
 - runs an example playbook via `ansible-runner`, using the container image for isolation.

The `pytz` example playbook uses a lookup plugin which requires python libraries `pytz` and `python-dateutil`.
A successful run proves that those dependencies are present in the execution environment.

#### Running Outside of ansible-runner

You can invoke the same example playbook manually.

```
docker run --rm --tty --interactive --mount "type=bind,src=$(pwd)/test/data/pytz,dst=/pytz" exec-env-pytz ansible-playbook -i localhost, /pytz/project/pytz.yml
```

### Integration Testing

These definitions are used in integration tests, for the `pytz` example:

```
py.test test/integration/test_build.py -k TestPytz
```
