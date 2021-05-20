ARG ANSIBLE_RUNNER_IMAGE=quay.io/ansible/ansible-runner:devel
ARG PYTHON_BUILDER_IMAGE=quay.io/ansible/python-builder:latest

FROM $PYTHON_BUILDER_IMAGE as python_builder
# =============================================================================
ARG ZUUL_SIBLINGS

# install this library (meaning ansible-builder)
COPY . /tmp/src
RUN assemble


FROM $ANSIBLE_RUNNER_IMAGE
# =============================================================================

COPY --from=python_builder /output/ /output
RUN /output/install-from-bindep && rm -rf /output

# move the assemble scripts themselves into this container
COPY --from=python_builder /usr/local/bin/assemble /usr/local/bin/assemble
COPY --from=python_builder /usr/local/bin/get-extras-packages /usr/local/bin/get-extras-packages

# building EEs require the install-from-bindep script, but not the rest of the /output folder
COPY --from=python_builder /output/install-from-bindep /output/install-from-bindep
