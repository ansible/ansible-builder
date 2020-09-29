# Ansible Builder

Ansible Builder is a tool that automates the process of building execution
environments using the schemas and tooling defined in various Ansible
Collections and by the user.


See the readthedocs page for `ansible-builder` at:

https://ansible-builder.readthedocs.io/en/latest/

## Execution Environments

Execution environments are container images intended to be used by Ansible
executors.  Starting in version 2.0,
[ansible-runner](https://github.com/ansible/ansible-runner) can make use of
these images.

An execution environment is expected to contain:

 - An install of Ansible (as `ansible-base` if 2.10 or higher)
 - An install of `ansible-runner`
 - Ansible collections
 - Python and/or system dependencies of
   - modules/plugins in collections
   - or content in `ansible-base`
   - or custom user needs

Execution environments contain everything needed to use Ansible modules and
plugins, as local actions, inside of automation.

## Get Involved:

* We use [GitHub issues](https://github.com/ansible/ansible-builder/issues) to
  track bug reports and feature ideas
* Want to contribute, check out our [guide](CONTRIBUTING.md)
* Join us in the `#ansible-builder` channel on Freenode IRC
* Join the discussion in
  [awx-project](https://groups.google.com/forum/#!forum/awx-project)
* For the full list of Ansible email Lists, IRC channels and working groups,
  check out the [Ansible Mailing
  lists](https://docs.ansible.com/ansible/latest/community/communication.html#mailing-list-information)
  page of the official Ansible documentation
  
## Code of Conduct

We ask all of our community members and contributors to adhere to the [Ansible
code of
conduct](http://docs.ansible.com/ansible/latest/community/code_of_conduct.html). If
you have questions, or need assistance, please reach out to our community team
at [codeofconduct@ansible.com](mailto:codeofconduct@ansible.com)

## License

[Apache License v2.0](./LICENSE.md)

## Project Maintainers:

- Shane McDonald (shanemcd@redhat.com)
- Alan Rominger (arominge@redhat.com)
- Bianca Henderson (bianca@redhat.com)

