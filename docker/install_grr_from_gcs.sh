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

mv -v "$INITIAL_DIR"/_artifacts/grr-server_*.tar.gz .

tar xzf grr-server_*.tar.gz

"${GRR_VENV}/bin/pip" install --no-index --no-cache-dir \
    --find-links=grr/local_pypi \
    grr/local_pypi/grr-response-proto-*.zip \
    grr/local_pypi/grr-response-core-*.zip \
    grr/local_pypi/grr-response-client-*.zip \
    grr/local_pypi/grr-api-client-*.zip \
    grr/local_pypi/grr-response-server-*.zip \
    grr/local_pypi/grr-response-test-*.zip \
    grr/local_pypi/grr-response-templates-*.zip

cd "${INITIAL_DIR}"
rm -rf "${WORK_DIR}"
