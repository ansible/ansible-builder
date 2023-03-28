Execution Environment Definition
================================

The execution environment (EE) definition file supports multiple versions.

  * Version 1: Supported by all ``ansible-builder`` versions.
  * Version 2: Supported by ``ansible-builder`` versions ``1.2`` and later.
  * Version 3: Supported by ``ansible-builder`` versions after ``1.2``.

If the EE file does not specify a version, version 1 will be assumed.

.. note::

    This version of the documentation discusses only the latest format version.
    For further details on older formats, reference previous versions of the
    documentation.

Version 3 Format
----------------

This version of the EE definition file offers substantially more configurability
and functionality over previous versions.

Below is an example version 3 EE file:

.. code:: yaml

    ---
    version: 3

    build_arg_defaults:
      ANSIBLE_GALAXY_CLI_COLLECTION_OPTS: '--pre'

    dependencies:
      galaxy: requirements.yml
      python:
        - six
        - psutil
      system: bindep.txt

    images:
      base_image:
        name: registry.redhat.io/ansible-automation-platform-21/ee-minimal-rhel8:latest

    additional_build_files:
        - src: files/ansible.cfg
          dest: configs

    additional_build_steps:
      prepend_galaxy:
        - ADD _build/configs/ansible.cfg ~/.ansible.cfg

      prepend_final: |
        RUN whoami
        RUN cat /etc/os-release
      append_final:
        - RUN echo This is a post-install command!
        - RUN ls -la /etc

Configuration
^^^^^^^^^^^^^

Below are listed the configuration YAML keys that you may use in the v3
format.

additional_build_files
**********************

This section allows you to add any file to the build context directory. These can
then be referenced or copied by `additional_build_steps` during any build stage.
The format is a list of dictionary values, each with a ``src`` and ``dest`` key and value.

Each list item must be a dictionary containing the following (non-optional) keys:

    ``src``
      Specifies the source file(s) to copy into the build context directory. This
      may either be an absolute path (e.g., ``/home/user/.ansible.cfg``),
      or a path that is relative to the execution environment file. Relative paths may be
      a glob expression matching one or more files (e.g. ``files/*.cfg``). Note
      that an absolute path may *not* include a regular expression. If ``src`` is
      a directory, the entire contents of that directory are copied to ``dest``.

    ``dest``
      Specifies a subdirectory path underneath the ``_build`` subdirectory of the
      build context directory that should contain the source file(s) (e.g., ``files/configs``).
      This may not be an absolute path or contain ``..`` within the path. This directory
      will be created for you if it does not exist.

additional_build_steps
**********************

This section enables you to specify custom build commands for any build phase.
These commands will be inserted directly into the instruction file for the
container runtime (e.g., `Containerfile` or `Dockerfile`). They will need to
conform to any rules required for the runtime system.

Below are the valid keys for this section. Each supports either a multi-line
string, or a list of strings.

    ``prepend_base``
      Commands to insert before building of the base image.

    ``append_base``
      Commands to insert after building of the base image.

    ``prepend_galaxy``
      Commands to insert before building of the galaxy image.

    ``append_galaxy``
      Commands to insert after building of the galaxy image.

    ``prepend_builder``
      Commands to insert before building of the builder image.

    ``append_builder``
      Commands to insert after building of the builder image.

    ``prepend_final``
      Commands to insert before building of the final image.

    ``append_final``
      Commands to insert after building of the final image.

build_arg_defaults
******************

Default values for build args can be specified in the definition file in
the ``build_arg_defaults`` section as a dictionary. This is an alternative
to using the :ref:`build-arg` CLI flag.

Build args used by ``ansible-builder`` are the following:

    ``ANSIBLE_GALAXY_CLI_COLLECTION_OPTS``
      This allows the user to pass the `--pre` flag (or others) to enable the installation of pre-release collections.

    ``ANSIBLE_GALAXY_CLI_ROLE_OPTS``
      This allows the user to pass any flags, such as `--no-deps`, to the role installation.

Values given inside of ``build_arg_defaults`` will be hard-coded into the
Containerfile, so they will persist if ``podman build`` is called manually.

If the same variable is specified in the CLI :ref:`build-arg` flag,
the CLI value will take higher precedence.

dependencies
************

This section allows you to describe any dependencies that will need to be
installed into the final image.

The following keys are valid for this section:

    ``ansible_core``
      The version of the Ansible python package to be installed. This value is
      passed directly to `pip` for installation and can be in any format that
      pip supports. Below are some example values:

      .. code:: yaml

        ansible_core: ansible-core
        ansible_core: ansible-core==2.14.3
        ansible_core: https://github.com/example_user/ansible/archive/refs/heads/ansible.tar.gz

    ``ansible_runner``
      The version of the Ansible Runner python package to be installed. This value is
      passed directly to `pip` for installation and can be in any format that
      pip supports. Below are some example values:

      .. code:: yaml

        ansible_runner: ansible-runner
        ansible_runner: ansible-runner==2.3.2
        ansible_runner: https://github.com/example_user/ansible-runner/archive/refs/heads/ansible-runner.tar.gz

    ``galaxy``
      Galaxy installation requirements. This may either be a filename, or a string
      representation of the file contents (see below for an example).

    ``python``
      The Python installation requirements. This may either be a filename, or a
      list of requirements (see below for an example).

    ``python_interpreter``
      A dictionary that defines the Python system package name to be installed by
      dnf (``package_name``) and/or a path to the Python interpreter to be used
      (``python_path``).

    ``system``
      The system requirements to be installed in bindep format. This may either
      be a filename, or a list of requirements (see below for an example).

The following example uses filenames that contain the various dependencies:

.. code:: yaml

    dependencies:
        python: requirements.txt
        system: bindep.txt
        galaxy: requirements.yml
        ansible_core: ansible-core==2.14.2
        ansible_runner: ansible-runner==2.3.1
        python_interpreter:
            package_name: "python310"
            python_path: "/usr/bin/python3.10"

And this example uses inline values:

.. code:: yaml

    dependencies:
        python:
          - pywinrm
        system:
          - iputils [platform:rpm]
        galaxy: |
          collections:
            - community.windows
            - ansible.utils
        ansible_core: ansible-core==2.14.2
        ansible_runner: ansible-runner==2.3.1
        python_interpreter:
            package_name: "python310"
            python_path: "/usr/bin/python3.10"

.. note::

  The ``|`` symbol is a YAML operator that allows you to define a block of text
  that may contain newline characters as a literal string. Because the ``galaxy``
  requirements content is expressed in YAML, we need this value to be a string
  of YAML so that we can pass it along to ``ansible-galaxy``.

images
******

This section is a dictionary that is used to define the base image to be used.
Verification of signed container images is supported with the ``podman`` container
runtime. How this data is used in relation to a Podman
`policy.json <https://github.com/containers/image/blob/main/docs/containers-policy.json.5.md>`_
file for container image signature validation depends on the value of the
:ref:`container-policy` CLI option.

  * ``ignore_all`` policy: Generate a `policy.json` file in the build
    :ref:`context directory <context>` where no signature validation is
    performed.

  * ``system`` policy: Signature validation is performed using pre-existing
    `policy.json` files in standard system locations. ``ansible-builder`` assumes
    no responsibility for the content within these files, and the user has complete
    control over the content.

  * ``signature_required`` policy: ``ansible-builder`` will use the container
    image definitions here to generate a `policy.json` file in the build
    :ref:`context directory <context>` that will be used during the build to
    validate the images.

Valid keys for this section are:

    ``base_image``
      A dictionary defining the parent image for the execution environment. A ``name``
      key must be supplied with the container image to use. Use the ``signature_original_name``
      key if the image is mirrored within your repository, but signed with the original
      image's signature key. Image names *MUST* contain a tag, such as ``:latest``.

options
*******

This section is a dictionary that contains keywords/options that can affect
builder runtime functionality. Valid keys for this section are:

    ``skip_ansible_check``
      This boolean value controls whether or not the check for an installation
      of Ansible and Ansible Runner is performed on the final image. Set this
      value to ``True`` to not perform this check. The default is ``False``.

Example ``options`` section:

.. code:: yaml

    options:
        skip_ansible_check: True

version
*******

This is an integer value that sets the version of the format being used. This
must be ``3`` for the v3 version.
