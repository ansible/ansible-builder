.. ansible-builder documentation master file, created by sphinx-quickstart on
   Tue Aug 18 18:59:26 2020.  You can adapt this file completely to your liking,
   but it should at least contain the root `toctree` directive.

Introduction
============

With ``ansible-builder`` you can configure and build portable, consistent, customized Ansible `control nodes`_ that are packaged as containers by Podman or Docker. These containers are known as Execution Environments. You can use execution environments on AWX or Ansible Controller, for local playbook development and testing, in your CI pipeline, and anywhere else you run automation. You can design and distribute specialized Execution Environments for your playbooks, choosing the versions of Python and ansible-core you want, and installing only the python packages, system packages, and Ansible Collections you need for each playbook.

.. contents::
   :local:

Container concepts and terms
----------------------------

Ansible Builder depends on more generalized containerization tools like Podman or Docker. Before you start using Ansible Builder, you should understand how containers and containerization tools work. Read the documentation for your preferred containerization tool.

Here are a few terms you should know. These concepts and terms are relevant to any use of containers, not specific to Ansible Builder.

  * Container: a package of code and dependencies that runs a service or an application across a variety of computing environments
  * Containerfile (called a Dockerfile in Docker): an instruction file for creating a container image by installing and configuring the code and dependencies  
  * Image: a complete but inactive version of a container - you can distribute images and create one or more containers based on each image

Execution Environments
----------------------

Execution Environments are container images that serve as Ansible `control
nodes`_. An Execution Environment contains:

- Python
- Ansible-core
- Ansible-runner
- Ansible Collections, if needed
- Python packages (anything you install with ``pip``)
- System packages (anything you install with ``dnf``, ``yum``, ``apt``, or other package managers)
- Other content you select and install

.. _control nodes:
   https://docs.ansible.com/ansible/latest/network/getting_started/basic_concepts.html#control-node


Getting Started
***************

To get started with Ansible Builder, you must install the ``ansible-builder`` utility and a containerization tool. Once you have the tools you need, create a file called ``execution_environment.yml``. This file is a :ref:`Execution Environment definition<Definition:Execution Environment Definition>`, where
you can specify the exact content you want to include in your
execution environment. You can specify these items:
- system packages (any packages installed with ``apt`` or ``yum``)
- the version of Python
- all Python packages (any packages installed with ``pip``)
- the version of ansible-core
- all Ansible Collections (anything installed with ``ansible-galaxy``)
- other items to download, install, or configure

Ansible Builder reads the ``execution_environment.yml`` file and can execute two separate steps. The first step is to create a containerfile and a build context. The second step is to run a containerization tool (Podman or Docker) to build an image. You can use ``ansible-builder build`` to run both steps. Or you can use ``ansible-builder create`` to run only the first step. For more details, read through the :ref:`Usage:CLI Usage`.

Collection Developers
^^^^^^^^^^^^^^^^^^^^^

When Ansible Builder installs Collections into an Execution Environment, it also installs each Collection's dependencies. You can learn to correctly declare dependencies for your collection from the :ref:`collection_metadata:Collection-level Metadata` page.


.. toctree::
   :maxdepth: 3
   :caption: Contents:

   self
   installation
   definition
   usage
   collection_metadata
   glossary
