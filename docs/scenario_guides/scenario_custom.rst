.. _custom_usage:

Building EEs with environment variables  and `ansible.cfg`
==========================================================

Ansible Builder version 3 schema allows users to perform complex scenarios
such as specifying custom Galaxy configurations.
You can use this approach to pass sensitive information, such as authentication tokens,
into the EE build without leaking them into the final EE image.

In the example below, we will take a look at

* Copying `ansible.cfg` file to an execution environment
* Using Galaxy Server environment variables

.. literalinclude:: galaxy_ee.yml
   :language: yaml


.. literalinclude:: galaxy_ansible.cfg
   :language: ini

In this example, the `additional_build_files` section allows you to add `ansible.cfg` to the build context directory.
Once this file is copied to the build context directory, it can be used in the build process.
In order to use the file, we need to copy it from the build context directory using the `COPY` directive specified in
the `prepend_galaxy` step of `additional_build_steps` section.

You can provide environment variables such as `ANSIBLE_GALAXY_SERVER_AUTOMATION_HUB_URL` and `ANSIBLE_GALAXY_SERVER_AUTOMATION_HUB_AUTH_URL`
using the `ENV` directive.
See `configuring Galaxy client <https://docs.ansible.com/ansible/latest/galaxy/user_guide.html#configuring-the-ansible-galaxy-client>`_ for more details.

For security reason, we do not want to store sensitive information in this case `ANSIBLE_GALAXY_SERVER_AUTOMATION_HUB_TOKEN`.
You can use `ARG` directive in order to receive the sensitive information from the user as an input. `--build-args` can be used
to provide this information while invoking the `ansible-builder` command.

.. seealso::

   :ref:`Execution Environment Definition version 3 <version_3_format>`
      The detailed documentation about EE definition version 3
