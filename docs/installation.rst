.. _builder_installation:

Installation
============

.. contents::
   :local:

Requirements
************

- To build images, you must install a containerization tool - either ``podman`` or ``docker`` - as well as the ``ansible-builder`` Python package.
- The ``--container-runtime`` option must correspond to the containerization tool you use.
- ``ansible-builder`` version ``3.x`` requires Python ``3.9`` or higher.

Install from PyPI
*****************

.. code-block:: shell

   $ pip3 install ansible-builder

.. note::

   An **alternative** approach to installing ``ansible-builder`` is using the ``ansible-dev-tools`` package. `Ansible Development Tools (ADT) <https://docs.ansible.com/projects/dev-tools/>`_ is a single Python package that includes all necessary tools to set up a development environment, generate new collections, build and test the content.

   .. code-block:: shell

      # This also installs ansible-core if it is not already installed
      $ pip3 install ansible-dev-tools

Install from Source
*******************

To install from the mainline development branch:

.. code-block:: shell

   $ pip3 install https://github.com/ansible/ansible-builder/archive/devel.zip

To install from a specific tag or branch, replace :code:`<ref>` in the following example:

.. code-block:: shell

   $ pip3 install https://github.com/ansible/ansible-builder/archive/<ref>.zip
