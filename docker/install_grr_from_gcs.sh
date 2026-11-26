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
    grr/local_pypi/grr_response_proto-*.tar.gz \
    grr/local_pypi/grr_response_core-*.tar.gz \
    grr/local_pypi/grr_response_client-*.tar.gz \
    grr/local_pypi/grr_api_client-*.tar.gz \
    grr/local_pypi/grr_response_server-*.tar.gz \
    grr/local_pypi/grr_response_test-*.tar.gz \
    grr/local_pypi/grr_response_templates-*.tar.gz

cd "${INITIAL_DIR}"
rm -rf "${WORK_DIR}"
