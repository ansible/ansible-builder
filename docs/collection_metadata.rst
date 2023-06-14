.. _builder_collection_metadata:

Collection-level dependencies
=============================

When Ansible Builder installs collections into an execution environment, it also installs the dependencies listed by each collection on Galaxy.

For Ansible Builder to find and install collection dependencies, those dependencies must be defined in one of these files:

* The ``meta/execution-environment.yml`` file containing the Python
  and/or bindep requirements or referencing other files listing them.
* The ``requirements.txt`` file in the root level of the collection.
* The ``bindep.txt`` file in the root level of the collection.

These files must be included in the packaged collection on Galaxy.
Ansible Builder cannot install dependencies listed in files that are included in
the ``build_ignore`` of a collection, because those files are not uploaded to Galaxy.

Dependency introspection
========================

If any dependencies are given, the introspection is run by Ansible Builder so that the requirements are sanitized (deduped) before container image assembly.

A user can see the introspection output during
the builder intermediate phase using the ``build -v3`` option.

How to verify collection-level metadata
=======================================

.. note::

  Running the introspect command described below is not a part of a typical workflow for building and using execution environments.

Collection developers can verify that dependencies specified in the collection will be processed correctly by Ansible Builder.

In order to do that, the collection has to be installed locally.

When installing collections using ansible-galaxy
------------------------------------------------

The easiest way to install a collection is to use the `ansible-galaxy <https://docs.ansible.com/ansible/latest/collections_guide/collections_installing.html#installing-collections-with-ansible-galaxy>`_
command which is a part of the ``ansible`` package.

Run the ``introspect`` command against your collection path:

::

    ansible-builder introspect --sanitize COLLECTION_PATH

The default collection path used by the ``ansible-galaxy`` command is ``~/.ansible/collections/``.
Read more about collection paths in the `Ansible configuration settings <https://docs.ansible.com/ansible/latest/reference_appendices/config.html#collections-paths>`_ guide.

The ``--sanitize`` option reviews all of the collection requirements and removes duplicates. It also removes any Python requirements that should normally be excluded (see :ref:`python_deps` below).

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

  ansible-builder introspect --sanitize ~/

.. _python_deps:

Python Dependencies
^^^^^^^^^^^^^^^^^^^

Ansible Builder combines all the Python requirements files from all collections into a single file using the ``requirements-parser`` library. This library supports complex syntax, including references to other files.

If multiple collections require the same *package name*, Ansible Builder combines them into a single entry and combines the constraints.

Certain package names are specifically *ignored* by ``ansible-builder``, meaning that Ansible Builder does not include them in the combined file of Python dependencies, even if a collection lists them as dependencies. These include test packages and packages that provide Ansible itself. The full list can be found in ``EXCLUDE_REQUIREMENTS`` in ``src/ansible_builder/_target_scripts/introspect.py``.

If you need to include one of these ignored package names, use the ``--user-pip`` option of the ``introspect`` command to list it in the user requirements file. Packages supplied this way are not processed against the list of excluded Python packages.

System-level Dependencies
^^^^^^^^^^^^^^^^^^^^^^^^^

For system packages, use the ``bindep`` format to specify cross-platform requirements, so they can be installed by whichever package management system the execution environment uses. Collections should specify necessary requirements for ``[platform:rpm]``.

Ansible Builder combines system package entries from multiple collections into a single file. Only requirements with *no* profiles (runtime requirements) are installed to the image. Entries from multiple collections which are outright duplicates of each other may be consolidated in the combined file.
