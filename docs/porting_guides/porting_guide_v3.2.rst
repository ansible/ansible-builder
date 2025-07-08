*********************************
Ansible Builder 3.2 Porting Guide
*********************************

This section discusses the behavioral changes between ``ansible-builder`` version 3.1 and version 3.2.

.. contents:: Topics

New Dependency Check of Installed Python Packages
=================================================

During the final build stage, immediately after all Python packages have been installed, a call
has been added to ``pip check`` to perform validation of installed package dependencies in the image.
If any dependency errors are identified, the build will now fail.

By default, this check is enabled. If you wish to disable this check, a new ``skip_pip_check`` option
has been added to the :ref:`options` section of the execution environment schema. Set this value to ``true``
to skip the new validation, as shown in the example below.

.. code-block:: yaml

   options:
     skip_pip_check: true
