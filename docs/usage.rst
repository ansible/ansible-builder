CLI Usage
=========

Once you have created a :ref:`definition<Definition:Execution Environment Definition>`, it's time to build
your Execution Environment.


The ``build`` command
---------------------

The ``ansible-builder build`` command takes an execution environment definition
as an input. It outputs the build context necessary for
building an execution environment image, and it builds that image. The
image can be re-built with the build context elsewhere, and give the
same result. By default, it looks for a file named ``execution-environment.yml``
in the current directory.

For our purposes here, we will use the following ``execution-environment.yml``
file as a starting point:


.. code:: yaml

    ---
    version: 1
    dependencies:
      galaxy: requirements.yml


The content of ``requirements.yml``:

.. code:: yaml

   ---
   collections:
     - name: awx.awx

To build an Execution Environment using the files above, run:

.. code::

   $ ansible-builder build
   ...
   STEP 7: COMMIT my-awx-ee
   --> 09c930f5f6a
   09c930f5f6ac329b7ddb321b144a029dbbfcc83bdfc77103968b7f6cdfc7bea2
   Complete! The build context can be found at: context

In addition to producing a ready-to-use container image, the build context is
preserved, which can be rebuilt at a different time and/or location with the
tooling of your choice.

``--tag``
*********

To customize the tagged name applied to the built image:

.. code::

   $ ansible-builder build --tag=my-custom-ee

More recent versions of ``ansible-builder`` support multiple tags:

.. code::

   $ ansible-builder build --tag=tag1 --tag=tag2

``--file``
**********

To use a definition file named something other than
``execution-environment.yml``:

.. code::

   $ ansible-builder build --file=my-ee.yml

``--galaxy-keyring``
********************

With more recent versions of Ansible, it is possible to have the ``ansible-galaxy``
utility verify collection signatures during installation. This requires a keyring to
be provided (can be built with GnuPG tooling) to use during verification. Provide
the path to this keyring with the ``--galaxy-keyring`` option. If this option is not
supplied, no signature verification will be performed. If it is provided, and the
version of Ansible is not recent enough to support this feature, an error will
occur during the image build process.

.. code::

   $ ansible-builder create --galaxy-keyring=/path/to/pubring.kbx
   $ ansible-builder build --galaxy-keyring=/path/to/pubring.kbx

``--galaxy-ignore-signature-status-code``
*****************************************

With ``--galaxy-keyring`` set it is possible to ignore certain errors that may occur while verifying collections.
It is passed unmodified to ``ansible-galaxy`` calls via the option ``--ignore-signature-status-code``.
See the ``ansible-galaxy`` documentation for more information.

.. code::

   $ ansible-builder create --galaxy-keyring=/path/to/pubring.kbx --galaxy-ignore-signature-status-code 500
   $ ansible-builder build --galaxy-keyring=/path/to/pubring.kbx --galaxy-ignore-signature-status-code 500

``--galaxy-required-valid-signature-count``
*******************************************

When ``--galaxy-keyring`` is set, the number of required valid collection signatures can be overridden.
The value is passed unmodified to ``ansible-galaxy`` calls via the option ``--required-valid-signature-count``.
See the ``ansible-galaxy`` documentation for more information.

.. code::

   $ ansible-builder create --galaxy-keyring=/path/to/pubring.kbx --galaxy-required-valid-signature-count 3
   $ ansible-builder build --galaxy-keyring=/path/to/pubring.kbx --galaxy-required-valid-signature-count 3


.. _context:

``--context``
*************

By default, a directory named ``context`` will be created in the current working
directory. To specify another location:

.. code::

   $ ansible-builder build --context=/path/to/dir


.. _build-arg:

``--build-arg``
***************

To use Podman or Docker's build-time variables, specify them the same way you would with ``podman build`` or ``docker build``.

By default, the Containerfile / Dockerfile outputted by Ansible Builder contains a build argument ``EE_BASE_IMAGE``, which can be useful for rebuilding Execution Environments without modifying any files.

.. code::

   $ ansible-builder build --build-arg FOO=bar

To use a custom base image:

.. code::

   $ ansible-builder build --build-arg EE_BASE_IMAGE=registry.example.com/another-ee


.. _container-runtime:

``--container-runtime``
***********************

Podman is used by default to build images. To use Docker:

.. code::

   $ ansible-builder build --container-runtime=docker


.. _container-policy:

``--container-policy``
**********************

.. note:: Added in version 1.2

Specifies the container image validation policy to use. This is valid only when
:ref:`container-runtime` is ``podman``. Valid values are one of:

* ``ignore_all``: Run podman with generated policy that ignores all signatures.
* ``system``: Relies on podman's consumption of system policy/signature with
  inline keyring paths. No builder-specific overrides are possible.
* ``signature_required``: Run podman with ``--pull-always`` and a generated
   policy that rejects all by default, with generated identity requirements for
   referenced container images, using an explicitly-provided keyring (specified
   with the :ref:`container-keyring` CLI option).

.. _container-keyring:

``--container-keyring``
***********************

.. note:: Added in version 1.2

Specifies the path to a GPG keyring file to use for validating container
image signatures.


``--verbosity``
***************

To customize the level of verbosity:

.. code::

   $ ansible-builder build --verbosity 2


``--prune-images``
******************

To remove unused images created after the build process:

.. code::

   $ ansible-builder build --prune-images

.. note::

   This flag essentially removes all the dangling images on the given machine whether they
   already exists or created by ansible-builder build process.


The ``create`` command
----------------------

The ``ansible-builder create`` command works similarly to the ``build`` command
in that it takes an execution environment definition as an input
and outputs the build context necessary for building an execution environment
image. However, the ``create`` command *will not* build the execution environment
image; this is useful for creating just the build context and a ``Containerfile``
that can then be shared.


Examples
--------

The example in ``test/data/pytz`` requires the ``awx.awx`` collection in
the execution environment definition. The lookup plugin
``awx.awx.tower_schedule_rrule`` requires the PyPI ``pytz`` and another
library to work. If ``test/data/pytz/execution-environment.yml`` file is
given to the ``ansible-builder build`` command, then it will install the
collection inside the image, read ``requirements.txt`` inside of the
collection, and then install ``pytz`` into the image.

The image produced can be used inside of an ``ansible-runner`` project
by placing these variables inside the ``env/settings`` file, inside of
the private data directory.


.. code:: yaml

    ---
    container_image: image-name
    process_isolation_executable: podman # or docker
    process_isolation: true

The ``awx.awx`` collection is a subset of content included in the default
AWX execution environment. More details can be found at the
`awx-ee <https://github.com/ansible/awx-ee>`__ repository.


Deprecated Features
-------------------

The ``--base-image`` CLI option has been removed.
See the ``--build-arg`` option for a replacement.
