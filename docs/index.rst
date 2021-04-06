.. ansible-builder documentation master file, created by sphinx-quickstart on
   Tue Aug 18 18:59:26 2020.  You can adapt this file completely to your liking,
   but it should at least contain the root `toctree` directive.

Introduction
============

Using Ansible content that depends on non-default dependencies can be tricky.
Packages must be installed on each node, play nicely with other software installed
on the host system, and be kept in sync.

To help simplify this process, we have introduced the concept of Execution
Environments, which you can create with Ansible Builder.


Execution Environments
----------------------

Execution Environments are container images that serve as Ansible `control
nodes`_. Starting in version 2.0, `ansible-runner
<https://ansible-runner.readthedocs.io/en/latest/execution_environments.html>`__
can make use of these images.

An Execution Environment is expected to contain:

- Ansible
- Ansible Runner
- Ansible Collections
- Python and/or system dependencies of:
   - modules/plugins in collections
   - content in ``ansible-base``
   - custom user needs

.. _control nodes:
   https://docs.ansible.com/ansible/latest/network/getting_started/basic_concepts.html#control-node

.. _ansible-runner: https://github.com/ansible/ansible-runner


Getting Started
***************

To get started with Ansible Builder, start by creating an
:ref:`Execution Environment definition<Definition:Execution Environment Definition>`. This
file allows you to specify which content you would like to include in your
execution environment, such as collections, Python requirements, and
system-level packages.

Once you have created a definition, read through the :ref:`Usage:CLI Usage`.

Collection Developers
^^^^^^^^^^^^^^^^^^^^^

Collection developers can declare requirements for their content by providing
the appropriate metadata. For more information, see
:ref:`collection_metadata:Collection-level Metadata`.


.. toctree::
   :maxdepth: 3
   :caption: Contents:

   self
   installation
   definition
   usage
   collection_metadata
   glossary
