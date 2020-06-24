# Ansible Builder Contributing Guidelines

If you have questions about this document or anything not covered here, come chat with us at `#ansible-awx` or `#ansible-builder` on irc.freenode.net


## Things to Know Before Submitting Code

- All code and doc submissions are done through pull requests against the `devel` branch.
- Take care to make sure no merge commits are in the submission, and use `git rebase` vs `git merge` for this reason.
- We ask all of our community members and contributors to adhere to the [Ansible code of conduct](http://docs.ansible.com/ansible/latest/community/code_of_conduct.html). If you have questions, or need assistance, please reach out to our community team at [codeofconduct@ansible.com](mailto:codeofconduct@ansible.com)


## Setting Up Your Development Environment

Ansible Builder development is powered by [Poetry](https://python-poetry.org/); make sure you have it [installed](https://python-poetry.org/docs/#installation) and then:

```bash
(host)$ poetry install
```

This will automatically set up the development environment under a virtualenv, which you can then switch to with:

```bash
(host)$ poetry shell
```

## Linting and Unit Tests

`tox` is used to run linters (`flake8` and `yamllint`) and unit tests on both Python 2 and 3. It uses Poetry to bootstrap these two environments.

## A Note About `setup.py`

In this repository you will find a [`setup.py` file](https://docs.python.org/3/installing/index.html#installing-index) (for downstream packaging purposes).  If your PR makes any changes to `pyproject.toml`, then this `setup.py` file needs to reflect those changes.  Poetry can help with this.

```bash
$ run poetry
$ run dephell deps convert --from=pyproject.toml --to=setup.py
```

A new `setup.py` file will be generated from these commands if edits are detected in `pyproject.toml`, which you can then commit along with any other changes.

## Gating and Merging

We require at least one approval on a pull request before it can be merged.  Merges are done through CI, via the `gate` label.
