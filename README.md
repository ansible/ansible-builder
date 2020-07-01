# Ansible Builder

Ansible Builder is a tool that automates the process of building execution environments using the schemas and tooling defined in various Ansible Collections and by the user.

## Execution Environments

Execution environments are container images intended to be used by Ansible executors.
Specifically, [ansible-runner](https://github.com/ansible/ansible-runner) can make use of these images.

An execution environment is expected to contain:

 - An install of Ansible (as `ansible-base` if 2.10 or higher)
 - An install of `ansible-runner`
 - Ansible collections
 - Python and/or system dependencies of
   - modules/plugins in collections
   - or content in `ansible-base`
   - or custom user needs

Execution environments contain everything needed to use Ansible modules
and plugins, as local actions, inside of automation.

## Execution Environment Definition

The `ansible-builder` CLI takes an execution environment definition as an input.
It can output either the files necessary for building the execution environment image,
or the image itself.
The schema of the execution environment definition looks like:

```yaml
---
version: 1
dependencies:
  galaxy: requirements.yml
  python: requirements.txt
```

The entries such as `requirements.yml` and `requirements.txt` may be a relative
path from the directory of the execution environment definition's folder,
or an absolute path.

## Get Involved:

* We use [GitHub issues](https://github.com/ansible/ansible-builder/issues) to track bug reports and feature ideas
* Want to contribute, check out our [guide](CONTRIBUTING.md)
* Join us in the `#ansible-builder` channel on Freenode IRC
* Join the discussion in [awx-project](https://groups.google.com/forum/#!forum/awx-project)
* For the full list of Ansible email Lists, IRC channels and working groups, check out the [Ansible Mailing lists](https://docs.ansible.com/ansible/latest/community/communication.html#mailing-list-information) page of the official Ansible documentation

## Project Maintainers:

Shane McDonald (shanemcd@redhat.com) <br>
Alan Rominger (arominge@redhat.com) <br>
Bianca Henderson (bianca@redhat.com)
