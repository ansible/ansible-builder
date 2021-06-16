# Ansible Builder Contributing Guidelines

If you have questions about this document or anything not covered here, come chat with us at `#ansible-awx` or `#ansible-builder` on irc.libera.chat


## Things to Know Before Submitting Code

- All code and doc submissions are done through pull requests against the `devel` branch.
- Take care to make sure no merge commits are in the submission, and use `git rebase` vs `git merge` for this reason.
- We ask all of our community members and contributors to adhere to the [Ansible code of conduct](http://docs.ansible.com/ansible/latest/community/code_of_conduct.html). If you have questions, or need assistance, please reach out to our community team at [codeofconduct@ansible.com](mailto:codeofconduct@ansible.com)


## Setting Up Your Development Environment

Inside of a virtual environment, simply run:

```bash
(ansible-builder) $ pip install -e .
```

## Linting and Unit Tests

`tox` is used to run linters (`flake8` and `yamllint`) and unit tests on both Python 2 and 3.


## Gating and Merging

We require at least one approval on a pull request before it can be merged.  Merges are done through CI, via the `gate` label.
