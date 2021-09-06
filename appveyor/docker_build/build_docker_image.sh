#!/bin/bash
#
# Script used by Appveyor to build Docker images for GRR.

set -ex

if [[ "${BRANCH}" == 'master' ]]; then
  readonly BUILD_TAG='grrdocker/grr:latest'
else
  readonly BUILD_TAG="grrdocker/grr:${BRANCH}"
fi

docker build -t "${BUILD_TAG}" .
