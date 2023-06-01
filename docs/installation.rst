Installation
============

.. contents::
   :local:

Requirements
************

- To build images, you must install either ``podman`` or ``docker``
  as well as the ``ansible-builder`` Python package.
- The ``--container-runtime`` option needs to correspond to the Podman/Docker
  executable you intend to use (where is this set?).
- ``ansible-builder`` version ``3.x`` requires Python ``???`` or higher.

Install from PyPi
*****************

.. code-block:: shell

   $ pip install ansible-builder


Install from Source
*******************

To install from the mainline development branch:

.. code-block:: shell

   $ pip install https://github.com/ansible/ansible-builder/archive/devel.zip

To install from a specific tag or branch, replace :code:`<ref>` in the following example:

.. code-block:: shell

   $ pip install https://github.com/ansible/ansible-builder/archive/<ref>.zip
