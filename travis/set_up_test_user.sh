#!/bin/bash

set -e

readonly DOCKER_USER=${DOCKER_USER:-grrbot}

useradd -m "${DOCKER_USER}"

# Group that owns the mounted GRR repo.
mountdir_gid="$(stat -c '%g' /mnt/grr)"
mountdir_grp_exists="$(cat /etc/group | grep "${mountdir_gid}" | wc -l)"

# Create group in container if it does not exist.
mountdir_gname='mntgrp'
if [[ "${mountdir_grp_exists}" == '0' ]]; then
  groupadd -g "${mountdir_gid}" "${mountdir_gname}"
else
  mountdir_gname="$(getent group "${mountdir_gid}" | cut -d: -f1)"
fi

# Make the test user an owner of the GRR repo.
usermod -a -G "${mountdir_gname}" "${DOCKER_USER}"

# Give the group owner write permission to the GRR repo.
# Note that any changes the test user makes inside
# the container will be reflected in the actual directory
# outside the container.
chmod -R g+w /mnt/grr
