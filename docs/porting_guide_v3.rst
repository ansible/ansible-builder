.. _porting_guide_v3:

Ansible Builder version 3 Porting Guide
=======================================

This section discusses the behavioral changes between ``ansible-builder`` 1.2 and ``ansible-builder`` 3.0.

It is intended to assist in updating your execution environment configuration files so they will work with this version of Ansible Builder.

We suggest you read this page along with `ansible-builder 3.0 release notes <https://github.com/ansible/ansible-builder/releases/tag/3.0.0>`_ to understand what updates you may need to make.

.. contents:: Topics

Overview
--------
The Ansible Builder 3.x execution environment definition file accepts seven top-level sections:

* additional_build_files
* additional_build_steps
* build_arg_defaults
* dependencies
* images
* options
* version

Porting options
---------------

You need to change the configuration YAML keys in your older (v1 and v2) execution environment file to the one listed here.

additional_build_files
^^^^^^^^^^^^^^^^^^^^^^

This is a new configuration that can be used to specify files to be added to the build context directory.
These can then be referenced or copied by `additional_build_steps` during any build stage.

See the :ref:`additional_build_files <additional_build_files>` section for more details.

additional_build_steps
^^^^^^^^^^^^^^^^^^^^^^

With Ansible Builder 3, you can specify more fine-grained build steps or custom commands for any build phase.
These commands will be inserted directly into the build instruction file for the
container runtime (For example, `Containerfile` or `Dockerfile`). The commands must conform to any rules required by the containerization tool.

These are additional build steps - 

* ``prepend_base``
* ``append_base``
* ``prepend_galaxy``
* ``append_galaxy``
* ``prepend_builder``
* ``append_builder``
* ``prepend_final``
* ``append_final``

See the :ref:`additional_build_steps <additional_build_steps>` section for more details.

dependencies
^^^^^^^^^^^^

Specifies dependencies to install into the final image, including ``ansible-core``, ``ansible-runner``, Python packages, system packages, and Ansible Collections. Ansible Builder automatically installs dependencies for any Ansible Collections you install.

In general, you can use standard syntax to constrain package versions. Use the same syntax you would pass to ``dnf``, ``pip``, ``ansible-galaxy``, or any other package management utility. You can also define your packages or collections in separate files and reference those files in the ``dependencies`` section of your execution environment definition file.

The following keys are valid for this section:

* ``ansible_core``
* ``ansible_runner``
* ``galaxy``
* ``python``
* ``python_interpreter``
* ``system``

See the :ref:`dependencies <dependencies>` section for more details.

images
^^^^^^

Specifies the base image to be used. At a minimum you *MUST* specify a source, image, and tag for the base image. The base image provides the operating system and may also provide some packages. We recommend using the standard ``host/namespace/container:tag`` syntax to specify images.

See the :ref:`images <images>` section for more details.

image verification
""""""""""""""""""
You can verify signed container images if you are using the ``podman`` container
runtime.

See the :ref:`image verification <image_verification>` section for more details.

options
^^^^^^^

A dictionary of keywords/options that can affect
builder runtime functionality. Valid keys for this section are:

* ``container_init``
* ``cmd``
* ``entrypoint``
* ``package_pip``
* ``package_manager_path``
* ``skip_ansible_check``
* ``relax_passwd_permissions``
* ``workdir``
* ``user``
* ``tags``

See the :ref:`options <options>` section for more details.

version
^^^^^^^

Must be ``3`` if you are using Ansible Builder 3.x.

See the :ref:`version <version>` section for more details.