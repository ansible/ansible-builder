# Ansible Builder Contributing Guidelines

If you are looking for community support, please visit the [Community guide](https://docs.ansible.com/projects/builder/en/latest/community/)
for information on how to get in touch.

## Code of Conduct

We ask all of our community members and contributors to adhere to the
[Ansible code of conduct](https://docs.ansible.com/projects/ansible/latest/community/code_of_conduct.html).
If you have questions, or need assistance, please reach out to our community team
at [codeofconduct@ansible.com](mailto:codeofconduct@ansible.com).

## Things to Know Before Submitting Code

### Start Small

If you are a new contributor, we recommend starting with a small change. This
will help you to become familiar with the project and the development process.
It will also help the maintainers to become familiar with you and build trust
with you. Attempting to tackle a large change, with little to no understanding
of the project, and with no input from maintainers, is likely to result in a
long review process and a frustrating experience for everyone involved.

### Using AI

We will accept contributions that have used AI to assist with code generation.
However, we expect you to fully understand any code you submit. When we ask
questions about your contributions during code review, please respond based on
your own understanding rather than delegating responses to your AI. We recommend
keeping AI-generated changes focused and incremental, as large AI-generated code
changes are challenging to review effectively.

### Tests Are Required

All code changes **must** include tests. There are very few exceptions to this rule. Understand
how the project test suite works and how to run the tests locally before submitting a pull request.

### Adding New Features

Adding new features is something we would like to see discussed beforehand via
a [feature request in GitHub](https://github.com/ansible/ansible-builder/issues/new?template=feature_request.yml).
Please do not submit a pull request that adds a new feature without first discussing it with the project maintainers.

### General Guidelines

- All code and documentation submissions are done through pull requests against the `devel` branch.
- Take care to make sure no merge commits are in the submission, and use `git rebase` instead `git merge` for this reason.

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
