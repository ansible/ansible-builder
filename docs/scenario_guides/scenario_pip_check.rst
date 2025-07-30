Validating Installed Python Dependencies
========================================

It is a good idea to verify that all of the installed Python packages have compatible
dependencies installed when the final container image is built. This is especially
important if you have excluded any external collection dependencies and manually
specified any replacements.

The ``pip`` utility includes a `check option <https://pip-python3.readthedocs.io/en/latest/reference/pip_check.html>`_
that can perform this validation. When ``pip check`` is run, it will do the validation of the
currently installed Python packages, and if any errors are identified, it will exit with a
non-zero status. A good place to call this check is during the end of the final build phase, just
after all dependencies have been installed. Add the code below to your execution
environment file to do the validation, which will fail the build if Python dependencies are not
satisfied:

.. code:: yaml

  additional_build_steps:
    append_final:
      - RUN $PYCMD -m pip check

Using the ``$PYCMD -m pip`` calling form, instead of calling ``pip`` directly, will guarantee that the same
Python executable that was used to install the Python packages is used to do the validation.
