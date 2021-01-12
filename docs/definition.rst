Execution Environment Definition
================================

An example execution environment definition schema is as follows:

.. code:: yaml

    ---
    version: 1

    build_arg_defaults:
      ANSIBLE_RUNNER_IMAGE: 'quay.io/ansible/ansible-runner:stable-2.10.devel'

    ansible_config: 'ansible.cfg'

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


Build Args and Base Image
^^^^^^^^^^^^^^^^^^^^^^^^^

Default values for build args can be specified in the definition file in
the ``default_build_args`` section as a dictionary. This is an alternative
to using the ``--build-arg`` CLI flag.

Build args used by ansible-builder are the following.

The ``ANSIBLE_GALAXY_CLI_COLLECTION_OPTS`` build arg allows the user to pass
the '--pre' flag to enable the installation of pre-releases collections.

The ``ANSIBLE_RUNNER_IMAGE`` build arg specifies the parent image
for the execution environment.

The ``PYTHON_BUILDER_IMAGE`` build arg specifies the image used for
compiling type tasks.

Values given inside of ``default_build_args`` will be hard-coded into the
Containerfile, so they will persist if ``podman build`` is called manually.

If the same variable is specified in the CLI ``--build-arg`` flag,
the CLI value will take higher precedence.

Ansible Config File Path
^^^^^^^^^^^^^^^^^^^^^^^^

When using an ``ansible.cfg`` file to pass a token and other settings for a
private account to an Automation Hub server, listing the config file path here
(as a string) will enable it to be included as a build argument in the initial
phase of the build.

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
