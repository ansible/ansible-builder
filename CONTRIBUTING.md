# Ansible Builder Contributing Guidelines

If you have questions about this document or anything not covered here, come chat with us at `#ansible-awx` or `#ansible-builder` on irc.libera.chat


## Things to Know Before Submitting Code

- All code and doc submissions are done through pull requests against the `devel` branch.
- Take care to make sure no merge commits are in the submission, and use `git rebase` vs `git merge` for this reason.
- We ask all of our community members and contributors to adhere to the [Ansible code of conduct](http://docs.ansible.com/ansible/latest/community/code_of_conduct.html). If you have questions, or need assistance, please reach out to our community team at [codeofconduct@ansible.com](mailto:codeofconduct@ansible.com)


## Setting Up Your Development Environment

Install `tox` if it is not already installed on your system. This can be done with `pip` or your system package manager.

```bash
pip install tox -c test/constraints.txt
```

Setup a test virtual environment and activate it:

```
tox -e dev
source .tox/dev/bin/activate
```

When done making changes, run:

```
deactivate
```

To reactivate the virtual environment:

```
source .tox/dev/bin/activate
```

## Testing

`tox` is used to run tests. To run the default set of tests, just run `tox`.

To list all available test targets, run `tox -a`.

Run a specific test with `tox -e [target]`



## Gating and Merging

We require at least one approval on a pull request before it can be merged. Merges are done through CI, via the `gate` label.
