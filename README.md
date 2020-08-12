# Ansible Builder

Ansible Builder is a tool that automates the process of building execution environments using the schemas and tooling defined in various Ansible Collections and by the user.

## Execution Environments

Execution environments are container images intended to be used by Ansible executors.
Starting in version 2.0, [ansible-runner](https://github.com/ansible/ansible-runner)
can make use of these images.

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

The `ansible-builder build` command takes an execution environment definition as an input.
It outputs the build context necessary for building an execution environment image,
and it builds that image.
The image can be re-built with the build context elsewhere, and give the same result.
The execution environment definition file needs to be in YAML format with the `.yml` file extension.

An example execution environment definition schema is as follows:

```yaml
---
version: 1
dependencies:
  galaxy: requirements.yml
  python: requirements.txt
  system: bindep.txt

additional_build_steps:
  prepend: |
    RUN whoami
    RUN cat /etc/os-release
  append:
    - RUN echo This is a post-install command!
    - RUN ls -la /etc
```

The entries such as `requirements.yml` and `requirements.txt` may be a relative path from the directory of the execution environment definition's folder, or an absolute path.

The `galaxy` entry points to a valid requirements file for the `ansible-galaxy collection install -r ...` command.
The `python` entry points to a python requirements file for `pip install -r ...`.
The `bindep` entry points to a [bindep](https://docs.openstack.org/infra/bindep/readme.html) requirements file.
This will be processed by `bindep` and then passed to `dnf`, other platforms are not yet supported.

Additional commands may be specified in the `additional_build_steps` section, either for before the main build steps (`prepend`) or after (`append`).  The syntax needs to be either a:
  - multi-line string (example shown in the `prepend` section above)
  - dictionary (as shown via `append`)

## Collection Execution Environment Dependencies

Collections inside of the `galaxy` entry of an execution environment will
contribute their python and system requirements to the image.

Requirements from a collection can be recognized in these ways:

 - A file `meta/execution-environment.yml` references the python and/or bindep requirements files
 - A file named `requirements.txt` is in the root level of the collection
 - A file named `bindep.txt` is in the root level of the collection

If any of these files are in the `build_ignore` of the collection, it will not work correctly.

Collection maintainers can verify that `ansible-builder` recognizes the requirements
they expect by using the introspect command. Example:

```
ansible-builder introspect --sanitize ~/.ansible/collections/
```

#### Collection Python Rules

Python requirements files are combined into a single file using the `requirements-parser` library
in order to support complex syntax like references to other files.

Entries from separate collections that give the same _package name_ will be combined
into the same entry, with the constraints combined.

There are several package names which are specifically _ignored_ by `ansible-builder`,
meaning that if a collection lists these, they will not be included in the combined file.
These include test packages and packages that provide Ansible itself.
The full list can be found in `EXCLUDE_REQUIREMENTS` in the `ansible_builder.requirements` module.

#### Collection System Requirement (bindep) Rules

The `bindep` format provides a way of specifying cross-platform requirements.
A minimum expectation is that collections specify necessary requirements for `[platform:rpm]`.

Entries from multiple collections will be combined into a single file.
Only requirements with _no_ profiles (runtime requirements) will be installed to the image.
Entries from multiple collections which are outright duplicates of each other
may be consolidated in the combined file.

### Example

The example in `test/data/pytz` requires the `awx.awx` collection in the execution environment definition.
The lookup plugin `awx.awx.tower_schedule_rrule` requires the PyPI `pytz` and another library to work.
If `test/data/pytz/execution-environment.yml` file is given to the `ansible-builder build` command,
then it will install the collection inside the image, read `requirements.txt` inside of the collection,
and then install `pytz` into the image.

The image produced can be used inside of an `ansible-runner` project by placing these variables
inside the `env/settings` file, inside of the private data directory.

```yaml
---
container_image: image-name
process_isolation_executable: podman
process_isolation: true
```

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
