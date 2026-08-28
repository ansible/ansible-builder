---
description: Review an Ansible Builder PR following the project's standardized process
argument-hint: <pr_number>
allowed-tools: [TodoWrite, Bash(gh pr view:*), Bash(gh pr diff:*), Bash(gh pr checkout:*), Bash(gh pr checks:*), Read, Grep, Glob, Search]
---

PR Review Command
=================

Review an Ansible Builder PR following the project's standardized process.

Usage
-----

```bash
/review <pr_number>
```

Arguments
---------

- `pr_number` (required): The GitHub PR number to review

Implementation
--------------

This command implements the PR review process for ansible-builder, which uses tox/pytest for testing and GitHub releases for changelog management.

Review Process Steps
--------------------

The command follows these numbered steps:

1. **Create TodoWrite list** for systematic review tracking
2. **Get PR details**: `gh pr view <number> -R ansible/ansible-builder` to understand scope, motivation and the desired outcome
3. **Get PR diff**: `gh pr diff <number> -R ansible/ansible-builder` to see all changes
4. **Check required components FIRST**:
   - Verify tests exist and specifically cover the changed code paths
   - Unit tests should be pytest style, and functional rather than tightly coupled to mocking
   - All source code changes MUST include tests (per CONTRIBUTING.md)
   - Check for appropriate test coverage in `test/unit/` or `test/integration/`
5. **Checkout PR branch**: `gh pr checkout <number> -R ansible/ansible-builder` to examine code holistically
6. **Review existing feedback**: `gh pr view <number> -R ansible/ansible-builder --comments` for all comments and previous reviews
7. **Verify all issues addressed**: Ensure CI failures, reviewer requests, and discussion points are resolved
8. **Call out unresolved feedback**: Explicitly mention any discussions/requests that remain unaddressed

Critical Review Elements
------------------------

- **Licensing**: Verify Apache License 2.0 compatibility for any new dependencies
- **Test scope**: Tests must exercise actual changed code, not just add random coverage
- **Changelog**: No changelog fragments needed - managed via GitHub releases
- **Testing**: Uses tox/pytest (not ansible-test). Check CI passes for linters, unit, and integration tests
- **Code quality**: Must pass `tox -e linters` (flake8, yamllint, mypy)

Each step is tracked in TodoWrite for visibility and systematic completion. A review round should not exceed 20 feedback items.
