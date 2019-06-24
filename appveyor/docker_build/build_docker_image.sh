#!/bin/bash
#
# Script used by Appveyor to build Docker images for GRR.

set -ex

if [[ "${APPVEYOR_REPO_BRANCH}" == 'master' ]]; then
  readonly BUILD_TAG='grrdocker/grr:latest'
else
  readonly BUILD_TAG="grrdocker/grr:${APPVEYOR_REPO_BRANCH}"
fi

docker build -t "${BUILD_TAG}" \
  --build-arg GCS_BUCKET="${GCS_BUCKET}" \
  --build-arg GRR_COMMIT="${APPVEYOR_REPO_COMMIT}" \
  .
