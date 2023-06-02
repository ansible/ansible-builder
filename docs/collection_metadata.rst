Collection-level Dependencies
=============================

When Ansible Builder installs Collections into an Execution Environment, it also installs the dependencies listed by each Collection on Galaxy.

For Ansible Builder to find and install collection dependencies, those dependencies must be defined in one of these files:

-  A file named ``meta/execution-environment.yml`` for Python
   and/or bindep requirements files
-  A file named ``requirements.txt`` in the root level of the
   collection
-  A file named ``bindep.txt`` in the root level of the collection

These files must be included in the packaged collection on Galaxy. Ansible Builder cannot install dependencies listed in files that are included in the ``build_ignore`` of a collection, because those files are not uploaded to Galaxy.

Collection maintainers can verify that ``ansible-builder`` recognizes
the requirements they expect by using the ``introspect`` command. For example:

.. code-block:: text

    ansible-builder introspect --sanitize ~/.ansible/collections/

The ``--sanitize`` option reviews all of the collection requirements and removes duplicates. It also removes any Python requirements that should normally be excluded (see :ref:`python_deps` below).

.. note::
    Use the ``-v3`` option to ``introspect`` to see logging messages about requirements that are being excluded.

.. _python_deps:

Python Dependencies
^^^^^^^^^^^^^^^^^^^

Ansible Builder combines all the Python requirements files from all collections into a single file using the ``requirements-parser`` library. This library supports complex syntax, including references to other files.

If multiple collections require the same *package name*, Ansible Builder combines them into a single entry and combines the constraints.

Certain package names are specifically *ignored* by ``ansible-builder``, meaning that Ansible Builder does not include them in the combined file of Python dependencies, even if a collection lists them as dependencies. These include test packages and packages that provide Ansible itself. The full list can be found in ``EXCLUDE_REQUIREMENTS`` in the ``ansible_builder.requirements`` module.

If you need to include one of these ignored package names, use the ``--user-pip`` option of the ``introspect`` command to list it in the user requirements file. Packages supplied this way are not processed against the list of excluded Python packages.

System-level Dependencies
^^^^^^^^^^^^^^^^^^^^^^^^^

For system packages, use the ``bindep`` format to specify cross-platform requirements, so they can be installed by whichever package management system the Execution Environment uses. Collections should specify necessary requirements for ``[platform:rpm]``.

Ansible builder combines system package entries from multiple collections into a single file. Only requirements with *no* profiles (runtime requirements) are installed to the image. Entries from multiple collections which are outright duplicates of each other may be consolidated in the combined file.
