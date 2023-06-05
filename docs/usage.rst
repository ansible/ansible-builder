CLI Usage
=========

Ansible Builder can execute two separate steps. The first step is to create a build instruction file (Containerfile for Podman, Dockerfile for Docker) and a build context based on your :ref:`definition<Definition:execution environment Definition>` file. The second step is to run a containerization tool (Podman or Docker) to build an image based on the build instruction file and build context. The ``ansible-builder build`` command executes both steps, giving you a build instruction file, a build context, and a fully built container image. The ``ansible-builder create`` command only executes the first step, giving you a build instruction file and a build context. If you use ``ansible-builder create``, you can use the resulting build instruction file and build context to build your container images on the platform of your choice.

.. contents::
   :local:

The ``build`` command
---------------------

The ``ansible-builder build`` command takes an execution environment definition file as an input. It outputs a build instruction file (Containerfile for Podman, Dockerfile for Docker), creates the build context necessary for building an execution environment image, and builds that image. The image can be re-built with the build context elsewhere, and give the same result. By default, it looks for a file named ``execution-environment.yml`` in the current directory.

This example uses the following ``execution-environment.yml``
file as a starting point:

.. code:: yaml

    ---
    version: 3
    dependencies:
      galaxy: requirements.yml


The content of ``requirements.yml``:

.. code:: yaml

   ---
   collections:
     - name: awx.awx

To build an execution environment using the files above, run:

.. code::

   $ ansible-builder build
   ...
   STEP 7: COMMIT my-awx-ee
   --> 09c930f5f6a
   09c930f5f6ac329b7ddb321b144a029dbbfcc83bdfc77103968b7f6cdfc7bea2
   Complete! The build context can be found at: context

Ansible Builder produces a ready-to-use container image and preserves the build context, which you can use to rebuild the image at a different time and/or location with the tooling of your choice.

Flags for the ``build`` command
-------------------------------

``--tag``
*********

Customizes the tagged name applied to the built image. To create an image with a custom name:

.. code::

   $ ansible-builder build --tag=my-custom-ee

More recent versions of ``ansible-builder`` support multiple tags:

.. code::

   $ ansible-builder build --tag=tag1 --tag=tag2

``--file``
**********

Specifies the execution environment file. To use a file named something other than ``execution-environment.yml``:

.. code::

   $ ansible-builder build --file=my-ee-def.yml

``--galaxy-keyring``
********************

Specifies a keyring for ``ansible-galaxy`` to use to verify collection signatures during installation. To verify collection signatures:

.. code::

   $ ansible-builder create --galaxy-keyring=/path/to/pubring.kbx
   $ ansible-builder build --galaxy-keyring=/path/to/pubring.kbx

If you do not pass this option, no signature verification is performed. If you do pass this option, but the version of Ansible is too old to support this feature, you will see an error during the image build process.

``--galaxy-ignore-signature-status-code``
*****************************************

Ignores certain errors that may occur while verifying collections. This option is passed unmodified to ``ansible-galaxy`` calls. Valid only when ``--galaxy-keyring`` is also set. See the ``ansible-galaxy`` documentation for more information.

.. code::

   $ ansible-builder create --galaxy-keyring=/path/to/pubring.kbx --galaxy-ignore-signature-status-code 500
   $ ansible-builder build --galaxy-keyring=/path/to/pubring.kbx --galaxy-ignore-signature-status-code 500

``--galaxy-required-valid-signature-count``
*******************************************

Overrides the number of required valid collection signatures. This option is passed unmodified to ``ansible-galaxy`` calls. Valid only when ``--galaxy-keyring`` is also set. See the ``ansible-galaxy`` documentation for more information.

.. code::

   $ ansible-builder create --galaxy-keyring=/path/to/pubring.kbx --galaxy-required-valid-signature-count 3
   $ ansible-builder build --galaxy-keyring=/path/to/pubring.kbx --galaxy-required-valid-signature-count 3


.. _context:

``--context``
*************

Specifies the directory name for the build context Ansible Builder creates. Default directory name is ``context`` in the current working directory. To specify another location:

.. code::

   $ ansible-builder build --context=/path/to/dir


.. _build-arg:

``--build-arg``
***************

Passes build-time arguments to Podman or Docker. Specify these flags or variables the same way you would with ``podman build`` or ``docker build``.

By default, the Containerfile / Dockerfile created by Ansible Builder contains a build argument ``EE_BASE_IMAGE``, which can be useful for rebuilding execution environments without modifying any files.

.. code::

   $ ansible-builder build --build-arg FOO=bar

To use different build arguments, you can specify ``--build-arg`` multiple times:

.. code::

   $ ansible-builder build --build-arg FOO=bar --build-arg SIMPLE=sample

To use a custom base image:

.. code::

   $ ansible-builder build --build-arg EE_BASE_IMAGE=registry.example.com/another-ee


.. _container-runtime:

``--container-runtime``
***********************

Specifies the containerization tool used to build images. Default is Podman. To use Docker:

.. code::

   $ ansible-builder build --container-runtime=docker


.. _container-policy:

``--container-policy``
**********************

.. note:: Added in version 1.2

Specifies the container image validation policy to use. Valid only when :ref:`container-runtime` is ``podman``. Valid values are one of:

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

Specifies the path to a GPG keyring file to use for validating container image signatures.


``--verbosity``
***************

Customizes the level of verbosity:

.. code::

   $ ansible-builder build --verbosity 2


``--prune-images``
******************

Removes unused images created after the build process:

.. code::

   $ ansible-builder build --prune-images

.. note::

   This flag removes all the dangling images on the given machine whether they already existed or were created by ``ansible-builder`` build process.


``--squash``
************

Controls the final image layer squashing. Valid values are:

* ``new``: Squash all of the final image's new layers into a single new layer
  (preexisting layers are not squashed).
* ``all``: Squash all of the final image's layers, including those inherited
  from the base image, into a single new layer.
* ``off``: Turn off layer squashing. This is the default.

.. note::

   This flag is compatible only with the ``podman`` runtime and will be ignored for any other runtime. Docker does not suport layer squashing; it is considered an experimental feature.


The ``create`` command
----------------------

The ``ansible-builder create`` command accepts an execution environment definition as an input and outputs the build context necessary for building an execution environment image. However, the ``create`` command *will not* build the execution environment image; this is useful for creating just the build context and a ``Containerfile`` that can then be shared.


Examples
--------

The example in ``test/data/pytz`` requires the ``awx.awx`` collection in the execution environment definition. The lookup plugin
``awx.awx.schedule_rrule`` requires the PyPI ``pytz`` and another
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
`awx-ee <https://github.com/ansible/awx-ee>`_ repository.


Deprecated Features
-------------------

The ``--base-image`` CLI option has been removed.
See the ``--build-arg`` option for a replacement.
