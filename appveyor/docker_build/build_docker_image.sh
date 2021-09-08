#!/bin/bash
#
# Script used by Appveyor to build Docker images for GRR.

set -ex

if [[ "${BRANCH}" == 'master' ]]; then
  readonly BUILD_TAG="${DOCKER_REPOSITORY}:latest"
else
  readonly BUILD_TAG="${DOCKER_REPOSITORY}:${BRANCH}"
fi

docker build -t "${BUILD_TAG}" .
