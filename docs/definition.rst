.. _builder_ee_definition:

Execution environment definition
================================

You define the content of your execution environment in a YAML file. By default, this file is called ``execution-environment.yml``
or ``execution-environment.yaml``. This file tells Ansible Builder how to create the build instruction file
(``Containerfile`` for Podman, ``Dockerfile`` for Docker) and build context for your container image.

.. note::
   This page documents the definition schema for Ansible Builder 3.x. If you are running an older version of Ansible Builder, you need an older schema version. Please consult older versions of the docs for more information. We recommend using version 3, which is more configurable and functional than previous versions.

.. contents::
   :local:

.. _version_3_format:

Overview
--------
The Ansible Builder 3.x execution environment definition file accepts seven top-level sections:

* additional_build_files
* additional_build_steps
* build_arg_defaults
* dependencies
* images
* options
* version

Version 3 sample files
----------------------

Below are some sample version 3 EE files. To use Ansible Builder 3.x, you must specify the schema version. If your EE file does not specify ``version: 3``, Ansible Builder will assume you want version 1.

This first simple example should successfully build an execution environment using the most recent ``ubi9`` base image and
the most recently compatible versions of ``ansible-core`` and ``ansible-runner`` for that image.

.. code:: yaml

   ---
   version: 3
   images:
     base_image:
       name: docker.io/redhat/ubi9:latest
   dependencies:
     ansible_core:
       package_pip: ansible-core
     ansible_runner:
       package_pip: ansible-runner

The second example below is more detailed and is not usable without modification and/or the creation of supporting
requirements and extra files, but does demonstrate more complete EE file syntax.

.. code:: yaml

    ---
    version: 3

    build_arg_defaults:
      ANSIBLE_GALAXY_CLI_COLLECTION_OPTS: '--pre'

    dependencies:
      ansible_core:
        package_pip: ansible-core==2.14.4
      ansible_runner:
        package_pip: ansible-runner
      galaxy: requirements.yml
      python:
        - six
        - psutil
      system: bindep.txt
      exclude:
        python:
          - docker
        system:
          - python3-Cython

    images:
      base_image:
        name: docker.io/redhat/ubi9:latest
        # Other available base images:
        #   - quay.io/rockylinux/rockylinux:9
        #   - quay.io/centos/centos:stream9
        #   - registry.fedoraproject.org/fedora:38
        #   - registry.redhat.io/ansible-automation-platform-23/ee-minimal-rhel8:latest
        #     (needs an account)

    # Custom package manager path for the RHEL based images
    # options:
    #  package_manager_path: /usr/bin/microdnf

    additional_build_files:
        - src: files/ansible.cfg
          dest: configs

    additional_build_steps:
      prepend_base:
        - RUN echo This is a prepend base command!
        # Enable Non-default stream before packages provided by it can be installed. (optional)
        # - RUN $PKGMGR module enable postgresql:15 -y
        # - RUN $PKGMGR install -y postgresql
      prepend_galaxy:
        - COPY _build/configs/ansible.cfg /etc/ansible/ansible.cfg

      prepend_final: |
        RUN whoami
        RUN cat /etc/os-release
      append_final:
        - RUN echo This is a post-install command!
        - RUN ls -la /etc

Configuration options
---------------------

You may use the configuration YAML keys listed here in your v3 execution environment definition file.

.. _additional_build_files:

additional_build_files
^^^^^^^^^^^^^^^^^^^^^^

Specifies files to be added to the build context directory. These can
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

.. _additional_build_steps:

additional_build_steps
^^^^^^^^^^^^^^^^^^^^^^

Specifies custom build commands for any build phase.
These commands will be inserted directly into the build instruction file for the
container runtime (e.g., `Containerfile` or `Dockerfile`). The commands must conform to any rules required by the containerization tool.

You can add build steps before or after any stage of the image creation process. For example, if you need ``git`` to be installed before you install your dependencies, you can add a build step at the end of the ``base`` build stage.

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

.. note::

    Please make sure that you do not specify `USER` directives in these build steps. This may lead to
    failures while building the image.
    If you want to override the `USER` setting, consider using the `options.user` setting mentioned below.

build_arg_defaults
^^^^^^^^^^^^^^^^^^

Specifies default values for build args as a dictionary. This is an alternative
to using the :ref:`build-arg` CLI flag.

Build args used by ``ansible-builder`` are the following:

    ``ANSIBLE_GALAXY_CLI_COLLECTION_OPTS``
      This allows the user to pass the `--pre` flag (or others) to enable the installation of pre-release collections.

    ``ANSIBLE_GALAXY_CLI_ROLE_OPTS``
      This allows the user to pass any flags, such as `--no-deps`, to the role installation.

    ``PKGMGR_PRESERVE_CACHE``
      This controls how often the package manager cache is cleared during the image build process.
      If this value is not set, which is the default, the cache is cleared frequently.
      If it is set to the string `always`, the cache is never cleared.
      Any other value forces the cache to be cleared only after the system dependencies are installed
      in the final build stage.

Ansible Builder hard-codes values given inside of ``build_arg_defaults`` into the
build instruction file, so they will persist if you run your container build manually.

If you specify the same variable in the execution environment definition and at the command line with the CLI :ref:`build-arg` flag, the CLI value will take higher precedence (the CLI value will override the value in the execution environment definition).

.. _dependencies:

dependencies
^^^^^^^^^^^^

Specifies dependencies to install into the final image, including ``ansible-core``, ``ansible-runner``, Python packages, system packages, and Ansible Collections. Ansible Builder automatically installs dependencies for any Ansible Collections you install.

In general, you can use standard syntax to constrain package versions. Use the same syntax you would pass to ``dnf``, ``pip``, ``ansible-galaxy``, or any other package management utility. You can also define your packages or collections in separate files and reference those files in the ``dependencies`` section of your execution environment definition file.

The following keys are valid for this section:

    ``ansible_core``
      The version of the ``ansible-core`` Python package to be installed. This value is
      a dictionary with a single key, ``package_pip``. The ``package_pip`` value
      is passed directly to `pip` for installation and can be in any format that
      pip supports. Below are some example values:

      .. code:: yaml

        ansible_core:
            package_pip: ansible-core
        ansible_core:
            package_pip: ansible-core==2.14.3
        ansible_core:
            package_pip: https://github.com/example_user/ansible/archive/refs/heads/ansible.tar.gz

    ``ansible_runner``
      The version of the Ansible Runner Python package to be installed. This value
      is a dictionary with a single key, ``package_pip``. The ``package_pip`` value
      is passed directly to `pip` for installation and can be in any format that
      pip supports. Below are some example values:

      .. code:: yaml

        ansible_runner:
            package_pip: ansible-runner
        ansible_runner:
            package_pip: ansible-runner==2.3.2
        ansible_runner:
            package_pip: https://github.com/example_user/ansible-runner/archive/refs/heads/ansible-runner.tar.gz

    ``galaxy``
      Ansible Collections to be installed from Galaxy. This may be a filename, a
      dictionary, or a multi-line string representation of an Ansible Galaxy
      ``requirements.yml`` file (see below for examples). Read more about
      the requirements file format in the `Galaxy user guide <https://docs.ansible.com/projects/ansible/latest/galaxy/user_guide.html#install-multiple-collections-with-a-requirements-file>`_.

    .. _python-pep508:

    ``python``
      The Python installation requirements. This may either be a filename, or a
      list of requirements (see below for an example).

      .. note::

        Python requirement specifications are expected to be limited to features defined by
        `PEP 508 <https://peps.python.org/pep-0508/>`_. Hash tag comments will always be allowed.
        Any deviation from this specification will be passed through to pip unverified and unaltered,
        although this is considered undefined and unsupported behavior. It is not recommended that
        you depend on this behavior.

    ``python_interpreter``
      A dictionary that defines the Python system package name to be installed by
      ``dnf`` (``package_system``) and/or a path to the Python interpreter to be used
      (``python_path``).

    ``system``
      The system packages to be installed, in bindep format. This may either
      be a filename, or a list of requirements (see below for an example).

    ``exclude``
      A dictionary defining the Python or system requirements to be excluded from the top-level dependency
      requirements of referenced collections. These exclusions will not apply to the user supplied Python or
      system dependencies, nor will they apply to dependencies of dependencies (top-level only).

      The following keys are valid for this section:

        * ``python`` - A list of Python dependencies to be excluded.
        * ``system`` - A list of system dependencies to be excluded.
        * ``all_from_collections`` - If you want to exclude *all* Python and system dependencies from one or
          more collections, supply a list of collection names under this key.

      The exclusion feature supports two forms of matching:

        * Simple name matching.
        * Advanced name matching using regular expressions.

      For simple name matching, you need only supply the name of the requirement/collection to match.
      All values will be compared in a case-insensitive manner.

      For advanced name matching, begin the exclusion string with the tilde (``~``) character to
      indicate that the remaining portion of the string is a regular expression to be used to match
      a requirement/collection name. The regex should be considered case-insensitive.

      .. note::
        The regular expression must match the full requirement/collection name. For example, ``~foo.``
        does not fully match the name ``foobar``, but ``~foo.+`` does.

      With both forms of matching, the exclusion string will be compared against the *simple* name of
      any Python or system requirement. For example, if you need to exclude the system requirement that
      appears as ``foo [!platform:gentoo]`` within an included collection, then your exclusion string should be
      ``foo``. To exclude the Python requirement ``bar == 1.0.0``, your exclusion string would be ``bar``.

      Example using both simple and advanced matching:

      .. code:: yaml

        dependencies:
            exclude:
                python:
                    - docker
                system:
                    - python3-Cython
                all_from_collections:
                    # Regular expression to exclude all from community collections
                    - ~community\..+

      .. note::
        The ``exclude`` option requires ``ansible-builder`` version ``3.1`` or newer.


The following example uses filenames that contain various dependencies:

.. code:: yaml

    dependencies:
        python: requirements.txt
        system: bindep.txt
        galaxy: requirements.yml
        ansible_core:
            package_pip: ansible-core==2.14.2
        ansible_runner:
            package_pip: ansible-runner==2.3.1
        python_interpreter:
            package_system: "python310"
            python_path: "/usr/bin/python3.10"

And this example uses inline values:

.. code:: yaml

    dependencies:
        python:
          - pywinrm
        system:
          - iputils [platform:rpm]
        galaxy:
          collections:
            - name: community.windows
            - name: ansible.utils
              version: 2.10.1
        ansible_core:
            package_pip: ansible-core==2.14.2
        ansible_runner:
            package_pip: ansible-runner==2.3.1
        python_interpreter:
            package_system: "python310"
            python_path: "/usr/bin/python3.10"

.. _images:

images
^^^^^^

Specifies the base image to be used. At a minimum you *MUST* specify a source, image, and tag for the base image. The base image provides the operating system and may also provide some packages. We recommend using the standard ``host/namespace/container:tag`` syntax to specify images. You may use Podman or Docker shortcut syntax instead, but the full definition is more reliable and portable.

Valid keys for this section are:

    ``base_image``
      A dictionary defining the parent image for the execution environment. A ``name``
      key must be supplied with the container image to use. Use the ``signature_original_name``
      key if the image is mirrored within your repository, but signed with the original
      image's signature key.

.. _image_verification:

image verification
""""""""""""""""""
You can verify signed container images if you are using the ``podman`` container
runtime. Set the :ref:`container-policy` CLI option to control how this data is used with a Podman
`policy.json <https://github.com/containers/image/blob/main/docs/containers-policy.json.5.md>`_
file for container image signature validation.

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

.. _options:

options
^^^^^^^

A dictionary of keywords/options that can affect
builder runtime functionality. Valid keys for this section are:

    ``container_init``
      A dictionary with keys that allow for customization of the container ``ENTRYPOINT`` and
      ``CMD`` directives (and related behaviors). Customizing these behaviors is an advanced
      task, and may result in subtle, difficult-to-debug failures. As the provided defaults for
      this section control several intertwined behaviors, overriding any value will skip all
      remaining defaults in this dictionary.
      Valid keys are:

      ``cmd``
        Literal value for the ``CMD`` Containerfile directive. The default value is ``["bash"]``.

      ``entrypoint``
        Literal value for the ``ENTRYPOINT`` Containerfile directive. The
        default entrypoint behavior handles signal propagation to subprocesses, as well as attempting to
        ensure at runtime that the container user has a proper environment with a valid writeable
        home directory, represented in ``/etc/passwd``, with the ``HOME`` envvar set to match. The default
        entrypoint script may emit warnings to ``stderr`` in cases where it is unable to suitably adjust the
        user runtime environment. This behavior can be ignored or elevated to a fatal error; consult the
        source for the ``entrypoint`` target script for more details. The default value is
        ``["/opt/builder/bin/entrypoint", "dumb-init"]``.

      ``package_pip``
        Package to install via pip for entrypoint support. This package will be installed in the final build image.
        The default value is ``dumb-init==1.2.5``.

    ``package_manager_path``
      A string with the path to the package manager (For example - ``dnf`` or ``microdnf``) to use.
      The default is ``/usr/bin/dnf``. This value will be used to install a
      Python interpreter, if specified in ``dependencies``, and during the
      build phase by the ``assemble`` script.

    ``skip_ansible_check``
      This boolean value controls whether or not the check for an installation
      of Ansible and Ansible Runner is performed on the final image. Set this
      value to ``True`` to not perform this check. The default is ``False``.

    ``skip_pip_install``
      This boolean value controls whether or not we attempt to install pip into
      the base image. Pip is necessary for Python requirement installation, among
      other things. You may choose to disable this step and handle installing
      pip manually if the current method of pip installation does not work for you.
      The default is ``False``.

    ``relax_passwd_permissions``
      This boolean value controls whether the ``root`` group (GID 0) is explicitly granted
      write permission to ``/etc/passwd`` in the final container image. The default entrypoint
      script may attempt to update ``/etc/passwd`` under some container runtimes with dynamically
      created users to ensure a fully functional POSIX user environment and home directory. Disabling
      this capability can cause failures of software features that require users to be listed in
      ``/etc/passwd`` with a valid and writeable home directory (eg, ``async`` in ansible-core, and the
      ``~username`` shell expansion). The default is ``True``.

    ``workdir``
      Default current working directory for new processes started under the final container
      image. Some container runtimes also use this value as ``HOME`` for dynamically-created
      users in the ``root`` (GID 0) group. When this value is specified, the directory will be
      created (if it doesn't already exist), set to ``root`` group ownership, and ``rwx`` group
      permissions recursively applied to it. The default value is ``/runner``.

    ``user``
      This sets the username or UID to use as the default user for the final container image.
      The default value ``1000``.

    ``tags``
      Specifies the names that are assigned to the resulting image if the build process completes successfully.
      The default value is ``ansible-execution-env:latest``.

Example ``options`` section:

.. code:: yaml

    options:
        container_init:
            package_pip: dumb-init>=1.2.5
            entrypoint: '["dumb-init"]'
            cmd: '["csh"]'
        package_manager_path: /usr/bin/microdnf
        relax_passwd_permissions: false
        skip_ansible_check: true
        workdir: /myworkdir
        user: bob
        tags:
          - ee_development:latest

.. _version:

version
^^^^^^^

An integer value that sets the schema version of the execution environment definition file. Defaults to ``1``. Must be ``3`` if you are using Ansible Builder 3.x.
