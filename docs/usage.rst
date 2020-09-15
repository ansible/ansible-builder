Ansible Builder Usage
=====================

The first part of this document is concerned with how the end-user writes the
execution environment definition.

Sections following that provide instructions for how a collection
maintainer should specify dependencies.

The final section gives an example.

Execution Environment Definition
--------------------------------

The ``ansible-builder build`` command takes an execution environment
definition as an input. It outputs the build context necessary for
building an execution environment image, and it builds that image. The
image can be re-built with the build context elsewhere, and give the
same result. The execution environment definition file needs to be in
YAML format with the ``.yml`` file extension.

An example execution environment definition schema is as follows:

.. code:: yaml

    ---
    version: 1
    dependencies:
      galaxy: requirements.yml
      python: requirements.txt
      system: bindep.txt

    additional_build_steps:
      prepend: |
        RUN whoami
        RUN cat /etc/os-release
      append:
        - RUN echo This is a post-install command!
        - RUN ls -la /etc

The entries such as ``requirements.yml`` and ``requirements.txt`` may be
a relative path from the directory of the execution environment
definition's folder, or an absolute path.

The ``galaxy`` entry points to a valid requirements file for the
``ansible-galaxy collection install -r ...`` command. The ``python``
entry points to a python requirements file for ``pip install -r ...``.
The ``bindep`` entry points to a
`bindep <https://docs.openstack.org/infra/bindep/readme.html>`__
requirements file. This will be processed by ``bindep`` and then passed
to ``dnf``, other platforms are not yet supported.

Additional commands may be specified in the ``additional_build_steps``
section, either for before the main build steps (``prepend``) or after
(``append``). The syntax needs to be either a: - multi-line string
(example shown in the ``prepend`` section above) - dictionary (as shown
via ``append``)

Collection Execution Environment Dependencies
---------------------------------------------

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

Collection Python Rules
^^^^^^^^^^^^^^^^^^^^^^^

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

Collection System Requirement (bindep) Rules
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``bindep`` format provides a way of specifying cross-platform
requirements. A minimum expectation is that collections specify
necessary requirements for ``[platform:rpm]``.

Entries from multiple collections will be combined into a single file.
Only requirements with *no* profiles (runtime requirements) will be
installed to the image. Entries from multiple collections which are
outright duplicates of each other may be consolidated in the combined
file.

Example
~~~~~~~

The example in ``test/data/pytz`` requires the ``awx.awx`` collection in
the execution environment definition. The lookup plugin
``awx.awx.tower_schedule_rrule`` requires the PyPI ``pytz`` and another
library to work. If ``test/data/pytz/execution-environment.yml`` file is
given to the ``ansible-builder build`` command, then it will install the
collection inside the image, read ``requirements.txt`` inside of the
collection, and then install ``pytz`` into the image.

The image produced can be used inside of an ``ansible-runner`` project
by placing these variables inside the ``env/settings`` file, inside of
the private data directory.

.. code:: yaml

    ---
    container_image: image-name
    process_isolation_executable: podman
    process_isolation: true
