Execution Environment Definition
================================

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


Ansible Galaxy Dependencies
^^^^^^^^^^^^^^^^^^^^^^^^^^^
The ``galaxy`` entry points to a valid requirements file for the
``ansible-galaxy collection install -r ...`` command. The ``python``
entry points to a python requirements file for ``pip install -r ...``.

The entry ``requirements.yml`` may be
a relative path from the directory of the execution environment
definition's folder, or an absolute path.

Python Dependencies
^^^^^^^^^^^^^^^^^^^

The ``python`` entry points to a valid requirements file for the
``pip install -r ...`` command.

The entry ``requirements.txt`` may be
a relative path from the directory of the execution environment
definition's folder, or an absolute path.

System-level Dependencies
^^^^^^^^^^^^^^^^^^^^^^^^^
The ``system`` entry points to a
`bindep <https://docs.openstack.org/infra/bindep/readme.html>`__
requirements file. This will be processed by ``bindep`` and then passed
to ``dnf``, other platforms are not yet supported.

Additional Custom Build Steps
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Additional commands may be specified in the ``additional_build_steps``
section, either for before the main build steps (``prepend``) or after
(``append``). The syntax needs to be either a: - multi-line string
(example shown in the ``prepend`` section above) - dictionary (as shown
via ``append``)
