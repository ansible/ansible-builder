#!/usr/bin/bash

#
# This script sets up a pulp all-in-one container (per the instructions at
# https://pulpproject.org/pulp-in-one-container/) that the builder tests can
# then use as an image repository that supports image signatures.
#

set -eux

##############################################################################
# Credentials for the RH registry account must be given and not be empty.
##############################################################################

if [ -z "$1" ] || [ -z "$2" ]
then
  echo "Usage: $0 <username> <password>"
  exit 1
fi

##############################################################################
# Add sigstore configurations for the images we wish to mirror.
##############################################################################

mkdir -p ~/.config/containers/registries.d
cat <<EOF >> ~/.config/containers/registries.d/registry.access.redhat.com.yaml
docker:
     registry.access.redhat.com:
         sigstore: https://access.redhat.com/webassets/docker/content/sigstore
EOF

cat <<EOF >> ~/.config/containers/registries.d/registry.redhat.io.yaml
docker:
     registry.redhat.io:
         sigstore: https://registry.redhat.io/containers/sigstore
EOF


##############################################################################
# Pull and run the pulp container
##############################################################################

podman pull docker.io/pulp/pulp:3.19

mkdir pulp
cd pulp
mkdir settings pulp_storage pgsql containers

echo "CONTENT_ORIGIN='http://$(hostname):8080'
ANSIBLE_API_HOSTNAME='http://$(hostname):8080'
ANSIBLE_CONTENT_HOSTNAME='http://$(hostname):8080/pulp/content'
TOKEN_AUTH_DISABLED=True" >> settings/settings.py

podman run --detach \
           --publish 8080:80 \
           --name pulp \
           --volume "$(pwd)/settings":/etc/pulp \
           --volume "$(pwd)/pulp_storage":/var/lib/pulp \
           --volume "$(pwd)/pgsql":/var/lib/pgsql \
           --volume "$(pwd)/containers":/var/lib/containers \
           --device /dev/fuse \
           pulp/pulp

##############################################################################
# Iteratively query the REST API until we get a JSON response (http code will
# be 200) which will indicate the system is ready.
##############################################################################

set +e
iter=0
httpcode=""

until [ "$httpcode" = "200" ]
do
  iter=$((iter+1))
  if [ $iter == 20 ]; then
    echo "Reached max iterations waiting for pulp container"
    exit 1
  fi
  sleep 10
  httpcode=$(curl -o /dev/null -s -w "%{http_code}\n" localhost:8080/pulp/api/v3/status/)
done
set -e

##############################################################################
# Set the 'admin' password and modify the pulp config with custom values.
##############################################################################

podman exec -it pulp bash -c 'pulpcore-manager reset-admin-password --password password'
pulp config create --base-url http://localhost:8080 --username admin --password password

##############################################################################
# Create an image repo called 'testrepo'
##############################################################################

pulp container repository create --name testrepo

##############################################################################
# Log in to the local and remote registries and copy the images we wish to
# mirror from remote to local repo. Remote login uses the username/password
# passed in to this script ($1 and $2). They are Github repo secrets. We are
# using a remote that requires authentication because we need a `builder`
# image (because builder requires builder, yuck) and no signed builder image
# is available in any open access repository, at this time.
#
# Setting XDG_RUNTIME_DIR is a workaround for some podman/skopeo issues.
# See https://github.com/containers/skopeo/issues/942 for more info.
##############################################################################

export XDG_RUNTIME_DIR=/tmp/pulptests
mkdir $XDG_RUNTIME_DIR

skopeo login --username admin --password password localhost:8080 --tls-verify=false
skopeo copy docker://registry.access.redhat.com/ubi9/ubi-micro:latest docker://localhost:8080/testrepo/ubi-micro --dest-tls-verify=false

podman login --username "$1" --password "$2" registry.redhat.io
skopeo copy docker://registry.redhat.io/ansible-automation-platform-21/ansible-builder-rhel8:latest docker://localhost:8080/testrepo/ansible-builder-rhel8 --dest-tls-verify=false
