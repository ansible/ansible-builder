CLI Usage
=========

Once you have created a :ref:`definition<Definition:Execution Environment Definition>`, it's time to build
your Execution Environment.


``ansible-builder build``
------------------------

The ``ansible-builder build`` command takes an execution environment
definition as an input. It outputs the build context necessary for
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


``--file``
**********

To use a definition file named something other than
``execution-environment.yml``:

.. code::

   $ ansible-builder build --file=my-ee.yml


``--context``
*************

By default, a directory named ``context`` will be created in the current working
directory. To specify another location:

.. code::

   $ ansible-builder build --context=/path/to/dir


``--build-arg``
*************

To use Podman or Docker's build-time variables, specify them the same way you would with ``podman build`` or ``docker build``.

By default, the Containerfile / Dockerfile outputted by Ansible Builder contains a build argument ``ANSIBLE_RUNNER_IMAGE``, which can be useful for rebuilding Execution Environments without modifying any files.

.. code::

   $ ansible-builder build --build-arg FOO=bar

To use a custom base image:

.. code::

   $ ansible-builder build --build-arg ANSIBLE_RUNNER_IMAGE=registry.example.com/another-ee


``--container-runtime``
***********************

Podman is used by default to build images. To use Docker:

.. code::

   $ ansible-builder build --container-runtime=docker


 ``--verbosity``
 ***************

 To customize the level of verbosity:

 .. code::

    $ ansible-builder build --verbosity 2


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
