.. _secret_passing:

Passing Secrets
===============

When creating an Execution Environment, it may be useful to use `build secrets <https://docs.docker.com/build/building/secrets/>`_.
This can be done with a combination of the use of :ref:`additional_build_steps` within the EE definition file, and the
:ref:`extra-build-cli-args` CLI option.

Use the :ref:`extra-build-cli-args` CLI option to pass a build CLI argument that defines the secret:

.. code::

    ansible-builder build --extra-build-cli-args="--secret id=mytoken,src=my_secret_file.txt"

Then, use a custom ``RUN`` command within your EE definition file that references this secret:

.. code:: yaml

    ---
    version: 3

    images:
      base_image:
        name: quay.io/centos/centos:stream9

    additional_build_steps:
      prepend_base:
        - RUN --mount=type=secret,id=mytoken TOKEN=$(cat /run/secrets/mytoken) some_command

    options:
      skip_ansible_check: true
