#!/bin/bash
#
# This script downloads sdists for a particular GRR github commit and
# installs them in a Docker image.

set -ex

function fatal() {
  >&2 echo "Error: ${1}"
  exit 1
}

INITIAL_DIR="${PWD}"
WORK_DIR=/tmp/docker_work_dir

mkdir "${WORK_DIR}"
cd "${WORK_DIR}"

mv -v "$INITIAL_DIR"/_artifacts/grr_server_*.tar.gz .

tar xzf grr_server-*.tar.gz

"${GRR_VENV}/bin/pip" install --no-index --no-cache-dir \
    --find-links=grr/local_pypi \
    grr/local_pypi/grr_response_proto-*.zip \
    grr/local_pypi/grr_response_core-*.zip \
    grr/local_pypi/grr_response_client-*.zip \
    grr/local_pypi/grr_api_client-*.zip \
    grr/local_pypi/grr_response_server-*.zip \
    grr/local_pypi/grr_response_test-*.zip \
    grr/local_pypi/grr_response_templates-*.zip

cd "${INITIAL_DIR}"
rm -rf "${WORK_DIR}"
