.. _env_usage:

Building EEs with environment variables
=======================================

Ansible Builder version 3 schema provides the option to specify environment variables which can be used in the build process.
See :ref:`version 3 schema <version_3_format>` for more details.

In the example below, we will take a look at specifying `ENV` variables.


.. literalinclude:: env_ee.yml
   :language: yaml

In this example, we are specifying an environment variable which may be required for the build process.
In order to achieve this functionality we are using the `ENV` variable
definition in the ``prepend_base`` step of the `additional_build_steps` section.

We can use the same environment variable in the later stage of the build process.

.. seealso::

   :ref:`Execution Environment Definition version 3 <version_3_format>`.
       The detailed documentation about EE definition version 3
