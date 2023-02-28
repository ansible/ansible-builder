Execution Environment Definition
================================

The execution environment (EE) definition file supports multiple versions.

  * Version 1: Supported by all ``ansible-builder`` versions.
  * Version 2: Supported by ``ansible-builder`` versions ``1.2`` and higher.

:ref:`Version 2 <version-2>` adds the capability to optionally use and verify
signed container images. This feature is only supported with the ``podman``
container runtime.

If the EE file does not specify a version, version 1 will be assumed.

.. _version-1:

Version 1 Format
----------------

An example version 1 execution environment definition schema is as follows:

.. code:: yaml

    ---
    version: 1

    build_arg_defaults:
      EE_BASE_IMAGE: 'quay.io/ansible/ansible-runner:latest'

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


The following keys are supported in this version of the EE file:

version
^^^^^^^

This integer value defines the version of the EE file. If not specified, the
default of ``1`` will be used.

build_arg_defaults
^^^^^^^^^^^^^^^^^^

Default values for build args can be specified in the definition file in
the ``build_arg_defaults`` section as a dictionary. This is an alternative
to using the ``--build-arg`` CLI flag.

Build args used by ``ansible-builder`` are the following:

``ANSIBLE_GALAXY_CLI_COLLECTION_OPTS``
  This allows the user to pass the '--pre' flag (or others) to enable the installation of pre-releases collections.

``ANSIBLE_GALAXY_CLI_ROLE_OPTS``
  This allows the user to pass the flags to the Role installation.

``EE_BASE_IMAGE``
  This string value specifies the parent image for the execution environment.

``EE_BUILDER_IMAGE``
  This string value specifies the image used for compiling type tasks.

Values given inside of ``build_arg_defaults`` will be hard-coded into the
Containerfile, so they will persist if ``podman build`` is called manually.

If the same variable is specified in the CLI ``--build-arg`` flag,
the CLI value will take higher precedence.

ansible_config
^^^^^^^^^^^^^^

When using an ``ansible.cfg`` file to pass a token and other settings for a
private account to an Automation Hub server, listing the config file path here
(as a string) will enable it to be included as a build argument in the initial
phase of the build.

dependencies
^^^^^^^^^^^^

This section is a dictionary value that is used to define the Ansible Galaxy,
Python, and system dependencies that must be installed into the final container.
Valid keys for this section are:

``galaxy``
  This string value is the path to a file containing the Ansible Galaxy
  dependencies to be installed with the ``ansible-galaxy collection install -r ...``
  command.

  The supplied value may be a relative path from the directory of the execution
  environment definition's folder, or an absolute path.

``python``
  This string value is the path to a file containing the Python dependencies
  to be installed with the ``pip install -r ...`` command.

  The supplied value may be a relative path from the directory of the execution
  environment definition's folder, or an absolute path.

``system``
  This string value is points to a
  `bindep <https://docs.openstack.org/infra/bindep/readme.html>`__
  requirements file. This will be processed by ``bindep`` and then passed
  to ``dnf``, other platforms are not yet supported.

additional_build_steps
^^^^^^^^^^^^^^^^^^^^^^

Additional commands may be specified in the ``additional_build_steps``
section, either for before the main build steps (``prepend``) or after
(``append``). The syntax needs to be one of the following:

- a multi-line string (example shown in the ``prepend`` section above)
- a list (as shown via ``append``)

.. _version-2:

Version 2 Format
----------------

With the version 2 format, an execution environment definition may specify
a base and builder container image whose signature must be validated before
builder will build the resulting image, based on the value of the
:ref:`container-policy` CLI option.

.. note::

    Although builder will create a `policy.json` file (see below) to control Podman image
    validation, it is up to the user to properly configure the Podman runtime to
    talk to the registries needed. This may include defining the sigstore for each
    registry, using secure connections (or not), etc. Such configuration is beyond
    the scope of this document.

This format is identical to the :ref:`version 1 format <version-1>`, except for
the following changes:

1. A new ``images`` key is added that supports more complex definitions of the
   base and builder images.
2. Defining ``EE_BASE_IMAGE`` or ``EE_BUILDER_IMAGE`` in the ``build_args_defaults``
   section, or with the :ref:`build-arg` CLI option, is no longer allowed.
3. The ``additional_build_steps`` section allows for specifying additional commands
   either before or after each of the four build phases (base/galaxy/builder/final).
   The version 1 format supported this for only the final build phase.
4. A new ``additional_build_files`` sections allows for including any file in
   the build context to be referenced at any image build stage.
5. The ``ansible_config`` keyword is removed. Similar functionality can be
   achieved through the use of ``additional_build_steps`` and ``additional_build_files``
   (see below for an example).

An example version 2 execution environment definition schema is as follows:

.. code:: yaml

    ---
    version: 2

    build_arg_defaults:
      ANSIBLE_GALAXY_CLI_COLLECTION_OPTS: '--pre'

    dependencies:
      galaxy: requirements.yml
      python: requirements.txt
      system: bindep.txt

    images:
      base_image:
        name: registry.redhat.io/ansible-automation-platform-21/ee-minimal-rhel8:latest
      builder_image:
        name: my-mirror.example.com/aap-mirror/ansible-builder-rhel8:latest
        signature_original_name: registry.redhat.io/ansible-automation-platform-21/ansible-builder-rhel8:latest

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

images
^^^^^^

This section is a dictionary that is used to define the base and builder images.
How this data is used in relation to a Podman
`policy.json <https://github.com/containers/image/blob/main/docs/containers-policy.json.5.md>`_
file for container image signature validation depends on the value of the
:ref:`container-policy` CLI option.

  * ``ignore_all`` policy: Generate a `policy.json` file in the build
    :ref:`context directory <context>` where no signature validation is
    performed. This duplicates the functionality under the
    :ref:`version 1 format<version-1>`.

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

``builder_image``
  A dictionary defining the image used for compiling type tasks.  A ``name``
  key must be supplied with the container image to use. Use the ``signature_original_name``
  key if the image is mirrored within your repository, but signed with the original
  image's signature key. Image names *MUST* contain a tag, such as ``:latest``.

additional_build_steps (v2)
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Similar to the version 1 format, you can specify custom build commands in this
section, but for all build phases.

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
  Commands to insert before building of the final image. This is the equivalent
  of the ``prepend`` version 1 keyword.

``append_final``
  Commands to insert after building of the final image. This is the equivalent
  of the ``append`` version 1 keyword.

additional_build_files
^^^^^^^^^^^^^^^^^^^^^^

This section allows you to add any file to the build context directory. These can
then be referenced at any of image build stages. The format is a list of dictionary
values, each with a ``src`` and ``dest`` key and value.

Each list item must be a dictionary containing the following (non-optional) keys:

``src``
  Specifies the source file(s) to copy into the build context directory. This
  may either be an absolute path (e.g., ``/home/user/.ansible.cfg``),
  or a path that is relative to the execution environment file. Relative paths may be
  a regular expression matching one or more files (e.g. ``files/*.cfg``). Note
  that the absolute path may *not* include a regular expression. If ``src`` is
  a directory, the entire contents of that directory are copied to ``dest``.

``dest``
  Specifies a subdirectory path underneath the ``_build`` subdirectory of the
  build context directory that should contain the source file(s) (e.g., ``files/configs``).
  This may not be an absolute path or contain ``..`` within the path. This directory
  will be created for you if it does not exist.
