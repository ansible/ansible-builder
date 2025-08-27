*********************************
Ansible Builder 3.2 Porting Guide
*********************************

This section discusses the behavioral changes between ``ansible-builder`` version 3.1 and version 3.2.

Deprecations
============

Execution environment schema versions 1 and 2 are deprecated and scheduled to be removed from Ansible Builder 3.3.
If you are currently using one of these versions, you will need to update your ``execution-environment.yml``
files to the :ref:`version 3 format <version_3_format>`.

A warning about the deprecation is sent to the logging output of the ``create`` or ``build`` commands when
an execution environment definition file is found to be using one of the deprecated versions.
