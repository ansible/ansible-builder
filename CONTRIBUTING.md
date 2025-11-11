# Ansible Builder Contributing Guidelines

If you are looking for community support, please visit
the [Community guide](https://docs.ansible.com/projects/builder/en/latest/community/)
for information on how to get in touch.

## Things to Know Before Submitting Code

- All code and documentation submissions are done through pull requests against
  the `devel` branch, unless you are creating a backport to an older release.
- Take care to make sure no merge commits are in the submission, and use
  `git rebase` vs `git merge` for this reason.
- All source code changes **MUST** include a test! We use `pytest` for testing.
- We ask all of our community members and contributors to adhere to the
  [Ansible code of conduct](https://docs.ansible.com/projects/ansible/latest/community/code_of_conduct.html).
  If you have questions, or need assistance, please reach out to our community
  team at [codeofconduct@ansible.com](mailto:codeofconduct@ansible.com).

## Setting Up Your Development Environment

Inside of a virtual environment, simply run:

```bash
  (ansible-builder) $ pip install -e .
```

## Linting, Unit, and Integration Tests

`tox` is used to run code linting (`flake8`, `yamllint`, and `mypy`), and to invoke
`pytest` to run unit and integration tests for Python 3. There are multiple `tox`
targets that use specific supported versions of Python. For example, to run the
linters tests for Python 3.11, you would execute:

```bash
  (ansible-builder) $ tox -e linters-py311
```

Some integration tests are marked as `destructive` (they can modify your container
runtime environment). You must pass a special flag if you want `tox` to run those.

```bash
  (ansible-builder) $ tox -e integration-py311 -- --run-destructive
```

By default, `tox` will attempt to use as many processes as it can on the
test system when running unit and integration tests. For finer grain control
of this, you should instead run `pytest` directly (see below).

### Running a Single Test

You can use `tox` to run all of the tests. For example:

```bash
  (ansible-builder) $ tox -e unit-py311
```

However, sometimes you just want to run a single test. To run only one test,
first use `tox` to build your selected virtual environment, then activate it
and run `pytest` directly.

```bash
  (ansible-builder) $ tox -e unit-py311 --notest
  (ansible-builder) $ source .tox/unit-py311/bin/activate
  (unit-py311) $ pytest -vvv -n1 test/unit/test_main.py::test_defnition_version
```

You have greater control over `pytest` options this way, like limiting it to
a single test, with a single thread, and with increased verbosity, as above.

Be aware that if you are going invoke `pytest` directly to run multiple tests,
we do mark several tests as `serial` so those should never be run in parallel.

### Skipping a Container Runtime

Tests marked with `test_all_runtimes` will be run with any container runtime
engine it can identify (for example, podman or docker). If you want to skip
one or more runtimes, use the `--skip-runtime` pytest option:

```bash
  (ansible-builder) $ tox -e integration-py311 -- --skip-runtime docker
```

## Gating and Merging

We require at least one approval on a pull request before it can be merged.
