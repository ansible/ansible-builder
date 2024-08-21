*********************************
Ansible Builder 3.1 Porting Guide
*********************************

This section discusses the behavioral changes between ``ansible-builder`` version 3.0 and version 3.1.

.. note::

    We highly advise running ``ansible-builder`` with increased verbosity using the ``-vvv`` option (``--v3`` for
    versions older than 3.1) to fully expose any error messages that may help in diagnosing any problems.

.. contents:: Topics

Python Requirements Handling
============================

The 3.1 release significantly changes how Python and system requirements are handled by simplifying dependency
parsing. This release removes the use of an external library that was unmaintained and parsed many types of
Python dependencies either partially or completely incorrectly. The changes are described below.

PEP 508 Standard
----------------

Python requirements files are expected to follow the `PEP 508 standard <https://peps.python.org/pep-0508/>`_.
Builder will *expect* the requirements file to be in this format, but it makes two exceptions:

#. Comments (lines beginning with ``#``) are ignored.
#. Any line from the requirements file that is not compliant with PEP508 causes a warning to be emitted and
   the line passed through to ``pip`` unmodified. It is not recommended to depend on this behavior, as
   it can change suddenly between ``pip`` releases, and can cause other problems with dependency resolution.

The passthrough of non-PEP508 compliant lines may expose issues that were hidden by the
version 3.0 dependency sanitizer, which often silently ignored and removed them.

Dependency Sanitization
-----------------------

Dependency sanitization (the combining of duplicate dependencies into a single dependency entry) is no longer performed by ``ansible-builder``.

.. note::

    The ``--sanitize`` option to the ``ansible-builder introspect`` command still exists, but is now undocumented
    and does nothing.

The effect of this change is that builder will now pass a listed dependency multiple times for each requirement file
in which it is found. For example, with version 3.0, if collection A listed the Python dependency ``foo``, and
collection B listed the dependency ``foo>=1.0``, then it would have appeared in the combined Python requirements file
as a single entry:

::

    foo,foo>=1.0   # from collection A, B

Now, with version 3.1, those dependencies are no longer combined and will appear in the combined Python requirements
file as separate entries:

::

    foo  # from collection A
    foo>=1.0  # from collection B

If your container image has an older version of ``pip``, this change might cause an error during the image build
process. This guide covers how to deal with this situation below.

Common Issues
=============

This section lists some common errors that might be encountered when running ``ansible-builder`` version 3.1.

ERROR: Double requirement given
-------------------------------

Because dependency sanitization has been removed, *all* Python requirements from included collections and user
requirement files are passed along to the ``pip`` command that installs those requirements. Due to this change,
the image build may exit abnormally with an error similar to the following:

::

    ERROR: Double requirement given: netaddr>=0.10.1 (from -r /tmp/src/requirements.txt (line 13)) (already in netaddr (from -r /tmp/src/requirements.txt (line 4)), name='netaddr')
    Error: building at STEP "RUN /output/scripts/assemble": while running runtime: exit status 1

This error comes from ``pip`` within one of the intermediate container images when attempting to install the Python
requirements from included collections and/or from the user supplied requirements. This intermediate image is based
on the base image defined within the Execution Environment file, and it means that the version of ``pip`` installed
within that image is too old to handle duplicate requirement entries.

To determine where the duplicate requirements are coming from, run ``ansible-builder`` with the ``-vvv`` option
to get more verbose output, then look for the output from the introspection phase. It will look similar to:

::

    [3/4] STEP 12/13: RUN $PYCMD /output/scripts/introspect.py introspect --write-bindep=/tmp/src/bindep.txt --write-pip=/tmp/src/requirements.txt
    Creating parent directory for /tmp/src/requirements.txt
    ---
    python:
    - 'netaddr  # from collection ansible.netcommon'
    - 'netaddr>=0.10.1  # from collection ansible.utils'

In the example output above, the double Python requirement for ``netaddr`` is coming from the collections
``ansible.netcommon`` and ``ansible.utils``.

The solution requires upgrading ``pip`` within the base image to a version that contains an updated dependency resolver.
Beginning with ``pip`` version 20.3, the dependency resolver can handle duplicate requirements whose versions do not
conflict, so that version is the minimum required. Upgrade ``pip`` in the base image from within the Execution
Environment file by adding these lines to it:

.. code-block:: yaml

    additional_build_steps:
      append_base:
        - RUN $PYCMD -m pip install -U pip

That will upgrade ``pip`` to the latest version within the base image. To restrict the upgrade to a specific
version of ``pip``, alter the upgrade command to specify that version. For example:

.. code-block:: yaml

    additional_build_steps:
      append_base:
        - RUN $PYCMD -m pip install -U pip==20.3
