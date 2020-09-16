Installation
============

In order to build images, you need to have either ``podman`` or ``docker``
installed as well as the ``ansible-builder`` python package.
The ``--container-runtime`` option needs to correspond to the podman/docker
executable you intend to use.

The following sections cover how to install ``ansible-builder``.


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
