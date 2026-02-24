.. ansible-builder documentation master file, created by sphinx-quickstart on
   Tue Aug 18 18:59:26 2020.  You can adapt this file completely to your liking,
   but it should at least contain the root `toctree` directive.

.. _builder_intro:

*******************************
Introduction to Ansible Builder
*******************************

With ``ansible-builder`` you can configure and build portable, consistent, customized Ansible control nodes that are packaged as containers by Podman or Docker.
These containers are known as execution environments. You can use them on AWX or Ansible Controller, with Ansible Navigator, for local playbook development and testing, in your CI pipelines, and anywhere else you run automation.

You can design and distribute specialized execution environments for your Ansible content, choosing the versions of Python and
ansible-core you want, and installing only the Python packages, system packages, and Ansible collections you need for your tasks.

.. note::

  Need help or want to discuss Ansible Builder including the documentation? See the :ref:`Community guide<community>` to learn how to join the conversation!

.. contents::
   :local:

Container concepts and terms
============================

Ansible Builder depends on more generalized containerization tools like Podman or Docker.

Before you start using Ansible Builder, you should understand the following concepts and terms relevant to any use of containers:

- **Build instruction file** (called a ``Containerfile`` in Podman and a ``Dockerfile`` in Docker): an instruction file for creating a container image by installing and configuring the code and dependencies.
- **Container**: a package of code and dependencies that runs a service or an application across a variety of computing environments.
- **Image**: a complete but inactive version of a container - you can distribute images and create one or more containers based on each image.

What are execution environments?
================================

Refer to the `Getting started with Execution Environments guide <https://docs.ansible.com/projects/ansible/devel/getting_started_ee/index.html>`_ for details.

Quickstart for Ansible Builder
==============================

To get started with Ansible Builder, you must install the ``ansible-builder`` utility and a containerization tool.

Once you have the tools you need, create an :ref:`execution environment definition <builder_ee_definition>` file.
By default, this file is called ``execution-environment.yml`` (the ``.yaml`` extension is also accepted).
In the execution environment definition file, you can specify the exact content you want to include in your
execution environment. You can specify these items:

- the base container image
- the version of Python
- the version of ansible-core
- the version of ansible-runner
- Ansible collections, with version restrictions
- system packages, with version restrictions
- Python packages, with version restrictions
- other items to download, install, or configure

 .. _choosing_base_image:

Choosing a base image
---------------------

RPM-based distributions are required
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. warning::

    Ansible Builder requires RPM-based container images that use the dnf or yum package manager.
    Non-RPM-based distributions (such as Debian, Ubuntu, or Alpine) are not supported and will fail to build.

Ansible Builder's default configuration and internal tooling assume the use of dnf/yum package management, which is present on RPM-based Linux distributions. The following examples are images that should work with Ansible Builder (this is not an exhaustive list):

- **Red Hat Universal Base Image (UBI)**: ``registry.access.redhat.com/ubi9/ubi:latest`` or ``docker.io/redhat/ubi9:latest``
- **CentOS Stream**: ``quay.io/centos/centos:stream9``
- **Rocky Linux**: ``quay.io/rockylinux/rockylinux:9``
- **Fedora**: ``registry.fedoraproject.org/fedora:43``
- **RHEL-based Ansible Automation Platform images**: ``registry.redhat.io/ansible-automation-platform-*/ee-*`` (requires Red Hat account)

.. note::

    These images are expected to work based on their use of RPM packaging and dnf/yum package managers.

When choosing a base image, prefer smaller images when possible, as they result in smaller final execution environment images. However, ensure you understand what packages are already installed on the base image to avoid redundant installations. For example, some base images already have Python installed, while others do not.

Non-RPM-based images are not supported
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. warning::

    Do not use Debian, Ubuntu, Alpine, or other non-RPM-based distributions as base images.
    These will fail during the build process because Ansible Builder's tooling expects dnf or yum package management.

Common errors when attempting to use non-RPM images include:

- **Package manager incompatibility**: The default package manager path (``/usr/bin/dnf``) does not exist on non-RPM distributions
- **System package installation failures**: Target scripts assume RPM-based package management tools

If you encounter build failures with your base image, ensure you are using an RPM-based distribution with dnf, yum, or microdnf available.

How Ansible Builder executes
============================

Ansible Builder can execute two separate steps:

- The first step is to create a build instruction file (``Containerfile`` for Podman, ``Dockerfile`` for Docker) and a build context based on the execution environment definition file.
- The second step is to run a containerization tool (Podman or Docker) to build an image based on the build instruction file and build context.

The ``ansible-builder build`` command runs both steps.

The ``ansible-builder create`` command runs only the first step. For more details, read through the :ref:`CLI usage docs <builder_cli>`.

How Ansible Builder builds images
---------------------------------

Ansible Builder executes four stages when it runs your containerization tool to build a container image.
The same four stages get executed if you build your container image directly with Podman or Docker, using a build instruction file and context generated by ``ansible-builder create``. These stages are:

1. **Base**: uses Podman or Docker to pull the base image you defined, then installs the Python version (if defined and different from any Python on the base image), pip, ansible-runner, and ansible-core or ansible. All three later stages of the build process build on the output of the Base stage.
2. **Galaxy**: downloads the collections you defined from Galaxy and stashes them locally as files.
3. **Builder**: downloads the other packages (Python packages and system packages) you defined and stash them locally as files.
4. **Final**: integrates the first three stages, installing all the stashed files on the output of the Base stage and generating a new image that includes all the content.

Ansible Builder injects hooks at each stage of the container build process so you can add custom steps before and after every build stage.

You may need to install certain packages or utilities before the Galaxy and Builder stages.
For example, if you need to install a collection from GitHub, you must install git after the Base stage to make it available during the Galaxy stage.

To add custom build steps, add an ``additional_build_steps`` section to your execution environment definition. For more details, read through the :ref:`CLI usage docs <builder_cli>`.

Defining collection dependencies
================================

When Ansible Builder installs collections into an execution environment, it also installs each collection's dependencies if they are specified.
Collection maintainers can learn to correctly declare dependencies for their collections from the :ref:`collection-level dependencies <builder_collection_metadata>` page.


.. toctree::
   :maxdepth: 3
   :caption: Contents:

   self
   community
   installation
   definition
   usage
   collection_metadata
   porting_guides/porting_guide
   glossary

.. toctree::
   :glob:
   :maxdepth: 1
   :caption: Common Scenarios

   scenario_guides/scenario_copy
   scenario_guides/scenario_using_env
   scenario_guides/scenario_custom
   scenario_guides/scenario_secret_passing
   scenario_guides/scenario_pip_check
