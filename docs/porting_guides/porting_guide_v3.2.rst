*********************************
Ansible Builder 3.2 Porting Guide
*********************************

This section discusses the behavioral changes between ``ansible-builder`` version 3.1 and version 3.2.

New Features
============

Disabling Colorized Output
--------------------------

Colorized terminal output can be disabled by either setting the ``NO_COLOR`` environment variable to
any non-empty value, or by setting the ``CLICOLOR`` environment variable to ``0``.

Behavior Changes
================

Preserve Symlinks During Additional Build File Copies
-----------------------------------------------------

When using symlinks in the ``additional_build_files`` section of an EE, previous behavior was to
dereference the symlink to copy the actual file into the container build context. If the symlink
pointed to a file that didn't exist, this would result in an error. The new behavior is to copy
the symlink itself. See `this issue <https://github.com/ansible/ansible-builder/issues/749>`_ for
more information.

Bindep Parse Error Detection
----------------------------

This release adds improved error detection and reporting for invalid ``bindep.txt`` files.
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
