.. _custom_usage:

Building EEs with environment variables for Galaxy configuration
================================================================

Ansible Builder version 3 schema allows users to perform complex scenarios
such as specifying custom Galaxy configurations.
You can use this approach to pass sensitive information, such as authentication tokens,
into the EE build without leaking them into the final EE image.

In the example below, we will take a look at

* Using Galaxy Server environment variables

.. literalinclude:: galaxy_ee.yml
   :language: yaml


You can provide environment variables such as ``ANSIBLE_GALAXY_SERVER_LIST``, ``ANSIBLE_GALAXY_SERVER_AUTOMATION_HUB_URL`` and ``ANSIBLE_GALAXY_SERVER_AUTOMATION_HUB_AUTH_URL`` using the ``ENV`` directive.
See `configuring Galaxy client <https://docs.ansible.com/projects/ansible/latest/galaxy/user_guide.html#configuring-the-ansible-galaxy-client>`_ for more details.

For security reasons, we do not want to store sensitive information in this case `ANSIBLE_GALAXY_SERVER_AUTOMATION_HUB_TOKEN`.
You can use `ARG` directive to receive sensitive information from the user as input. `--build-args` can be used
to provide this information while invoking the `ansible-builder` command.

.. seealso::

   :ref:`Execution Environment Definition version 3 <version_3_format>`
      The detailed documentation about EE definition version 3
