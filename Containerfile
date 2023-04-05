ARG BASE_IMAGE=registry.access.redhat.com/ubi9:9.1.0-1782

FROM $BASE_IMAGE as base
RUN python3 -m ensurepip && python3 -m pip install --upgrade pip

FROM base as builder
# build this library (meaning ansible-builder)
COPY . /tmp/src
COPY ./ansible_builder/_target_scripts/* /output/scripts/
RUN python3 -m pip install --no-cache-dir bindep wheel && /output/scripts/assemble

FROM base
COPY --from=builder /output/ /output
# building EEs require the install-from-bindep script, but not the rest of the /output folder
RUN /output/scripts/install-from-bindep && find /output/* -not -name install-from-bindep -exec rm -rf {} +

# copy the assemble scripts themselves into this container
COPY ./ansible_builder/_target_scripts/assemble /usr/local/bin/assemble
COPY ./ansible_builder/_target_scripts/get-extras-packages /usr/local/bin/get-extras-packages
