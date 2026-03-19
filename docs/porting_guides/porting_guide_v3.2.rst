*********************************
Ansible Builder 3.2 Porting Guide
*********************************

This section discusses the behavioral changes between ``ansible-builder`` version 3.1 and version 3.2.

Behavior Changes
================

Bindep Parse Error Detection
----------------------------

The 3.2 release adds improved error detection and reporting for invalid ``bindep.txt`` files.
Previously, when ``bindep`` encountered unparsable content in a ``bindep.txt`` file, the build
would continue and potentially fail later with unclear error messages. Now, the build will fail
immediately with a clear error message when bindep reports a parse error.

When the ``bindep`` program exits with code 2 (indicating unparsable content in ``bindep.txt``),
the build process will now:

#. Stop immediately at the point where the parse error is detected
#. Output a clear error message: ``Error: bindep.txt contains unparsable content``
#. Exit with code 2

This change affects the ``assemble`` script that runs during the builder phase of execution
environment creation.

.. note::
  This behavior change requires your container image have ``bindep`` version 2.14.0 or higher installed.
  Versions below this will not halt execution on unparsable content.

Deprecations
============

Execution environment schema versions 1 and 2 are deprecated and scheduled to be removed from Ansible Builder 3.3.
If you are currently using one of these versions, you will need to update your ``execution-environment.yml``
files to the :ref:`version 3 format <version_3_format>`.

A warning about the deprecation is sent to the logging output of the ``create`` or ``build`` commands when
an execution environment definition file is found to be using one of the deprecated versions.
