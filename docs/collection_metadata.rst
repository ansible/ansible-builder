Collection-level Metadata
=========================

Collections inside of the ``galaxy`` entry of an execution environment
will contribute their python and system requirements to the image.

Requirements from a collection can be recognized in these ways:

-  A file ``meta/execution-environment.yml`` references the python
   and/or bindep requirements files
-  A file named ``requirements.txt`` is in the root level of the
   collection
-  A file named ``bindep.txt`` is in the root level of the collection

If any of these files are in the ``build_ignore`` of the collection, it
will not work correctly.

Collection maintainers can verify that ``ansible-builder`` recognizes
the requirements they expect by using the introspect command. Example:

::

    ansible-builder introspect --sanitize ~/.ansible/collections/

Python Dependencies
^^^^^^^^^^^^^^^^^^^

Python requirements files are combined into a single file using the
``requirements-parser`` library in order to support complex syntax like
references to other files.

Entries from separate collections that give the same *package name* will
be combined into the same entry, with the constraints combined.

There are several package names which are specifically *ignored* by
``ansible-builder``, meaning that if a collection lists these, they will
not be included in the combined file. These include test packages and
packages that provide Ansible itself. The full list can be found in
``EXCLUDE_REQUIREMENTS`` in the ``ansible_builder.requirements`` module.

System-level Dependencies
^^^^^^^^^^^^^^^^^^^^^^^^^

The ``bindep`` format provides a way of specifying cross-platform
requirements. A minimum expectation is that collections specify
necessary requirements for ``[platform:rpm]``.

Entries from multiple collections will be combined into a single file.
Only requirements with *no* profiles (runtime requirements) will be
installed to the image. Entries from multiple collections which are
outright duplicates of each other may be consolidated in the combined
file.
