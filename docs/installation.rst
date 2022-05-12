Installation
============

Requirements
************

- In order to build images, you need to have either ``podman`` or ``docker``
  installed as well as the ``ansible-builder`` Python package.
  The ``--container-runtime`` option needs to correspond to the Podman/Docker
  executable you intend to use.
- ``ansible-builder`` version ``1.1.0`` requires Python ``3.8`` or higher.


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
