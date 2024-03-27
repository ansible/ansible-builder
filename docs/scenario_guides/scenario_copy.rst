.. _copy_usage:

Copying arbitrary files to EE
=============================

Ansible Builder version 3 schema provides the option to copy files to an EE image.
See  the :ref:`version 3 schema <version_3_format>` for more details.

In the example below, we will take a look at copying arbitrary files to an execution environment.


.. literalinclude:: copy_ee.yml
   :language: yaml

In this example, the `additional_build_files` section allows you to add `rootCA.crt` to the build context directory.
Once this file is copied to the build context directory, it can be used in the build process.
In order to use, the file,  we need to copy it from the build context directory using  the `COPY` directive specified in
the `prepend_base` step of `additional_build_steps` section.

Finally, you can perform any action based upon the copied file, such as in this example updating
dynamic configuration of CA certificates by running `RUN update-ca-trust`.

.. seealso::

   :ref:`Execution Environment Definition version 3 <version_3_format>`
      The detailed documentation about EE definition version 3
