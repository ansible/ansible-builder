.. _builder_collection_metadata:

Collection-level dependencies
=============================

When Ansible Builder installs collections into an execution environment, it also installs their controller-side Python or system package dependencies listed by each collection on Galaxy.

For Ansible Builder to find and install collection dependencies, those dependencies must be defined in files in a collection repository.

.. note::

  If present, the files below must be included in the packaged collection on Galaxy.
  Ansible Builder cannot install dependencies listed in files that are included in the ``build_ignore`` of a collection, because those files are not included in the collection artifact.

If you are a collection maintainer, make sure the controller-side dependencies are specified and :ref:`verified<verify_collection_metadata>`.

We recommend you specify paths to dependency files in the ``meta/execution-environment.yml`` file.
Here is an example of its content:

.. code:: yaml

    dependencies:
      python: meta/ee-requirements.txt  # List Python package requirements in the file
      system: meta/ee-bindep.txt  # List system package requirements in the file

If the ``meta/execution-environment.yml`` file is not present, by default, Ansible Builder will expect the dependencies to be defined in:

* the ``requirements.txt`` file in the collection root directory for Python package requirements
* the ``bindep.txt`` file in the collection root directory for system package requirements

.. note::

  If your collection uses the ``requirements.txt`` or ``bindep.txt`` files in its root directory for anything else but its controller-side dependencies, for example, for listing testing requirements, make sure you use the ``meta/execution-environment.yml`` file to specify other dependency files for execution environment purposes.

Dependency introspection
========================

If any dependencies are given, the introspection is run by Ansible Builder so that the requirements are found before container image assembly.

A user can see the introspection output during
the builder intermediate phase using the ``build -v3`` option.

.. _verify_collection_metadata:

How to verify collection-level metadata
=======================================

.. note::

  Running the introspect command described below is not part of a typical workflow for building and using execution environments.

Collection developers can verify that dependencies specified in the collection will be processed correctly by Ansible Builder.

To do that, the collection has to be installed locally.

When installing collections using ansible-galaxy
------------------------------------------------

The easiest way to install a collection is to use the `ansible-galaxy <https://docs.ansible.com/projects/ansible/latest/collections_guide/collections_installing.html#installing-collections-with-ansible-galaxy>`_
command which is a part of the ``ansible`` package.

Run the ``introspect`` command against your collection path:

::

    ansible-builder introspect COLLECTION_PATH

The default collection path used by the ``ansible-galaxy`` command is ``~/.ansible/collections/``.
Read more about collection paths in the `Ansible configuration settings <https://docs.ansible.com/projects/ansible/latest/reference_appendices/config.html#collections-paths>`_ guide.

.. note::
    Use the ``-v3`` option to ``introspect`` to see logging messages about requirements that are being excluded.

When installing collections manually
------------------------------------

If you download collection tarballs from `Galaxy <https://galaxy.ansible.com/>`_  manually or clone collection git repositories,
for the ``introspect`` command to work properly, be sure you store your collections
using the following directory structure:

::

   ansible_collections/NAMESPACE/COLLECTION

For example, if you need to inspect the ``community.docker`` collection, the path will be:

::

  ansible_collections/community/docker

Then, if the ``ansible_collection`` directory is in your home directory, you can run ``introspect`` with the following command:

::

  ansible-builder introspect ~/

.. _python_deps:

Python Dependencies
^^^^^^^^^^^^^^^^^^^

Ansible Builder combines all the Python requirements files from all collections into a single file.

Certain package names are specifically *ignored* by ``ansible-builder``, meaning that Ansible Builder
does not include them in the combined file of Python dependencies, even if a collection lists them as
dependencies. These include test packages and packages that provide Ansible itself. The full list can
be found in ``EXCLUDE_REQUIREMENTS`` in ``src/ansible_builder/_target_scripts/introspect.py``.

If you need to include one of these ignored package names, use the ``--user-pip`` option of the
``introspect`` command to list it in the user requirements file. Packages supplied this way are
not processed against the list of excluded Python packages.

.. note::

  These dependencies are subject to the same `PEP 508 <https://peps.python.org/pep-0508/>`_ format
  restrictions described for Python requirements in the :ref:`EE definition specification <python-pep508>`.

System-level Dependencies
^^^^^^^^^^^^^^^^^^^^^^^^^

For system packages, use the ``bindep`` format to specify cross-platform requirements, so they can be installed by whichever package management system the execution environment uses. Collections should specify necessary requirements for ``[platform:rpm]``.

Ansible Builder combines system package entries from multiple collections into a single file.

* Requirements with ``compile`` profile indicate that these requirements are needed to install other requirements (especially Python ones), but are not required to be in the final build.
* Requirements with ``epel`` profile indicate that EPEL repositories will be enabled before installing these requirements.
* Only requirements with *no* profiles (runtime requirements) are installed to the image.

Entries from multiple collections which are outright duplicates of each other may be consolidated in the combined file.
