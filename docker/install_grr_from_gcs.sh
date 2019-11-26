#!/bin/bash
#
# This script downloads sdists for a particular GRR github commit and
# installs them in a Docker image.

set -e

function fatal() {
  >&2 echo "Error: ${1}"
  exit 1
}

if [[ -z "${GCS_BUCKET}" ]]; then
  fatal "GCS_BUCKET must be set!"
fi

if [[ -z "${GRR_COMMIT}" ]]; then
  fatal "GRR_COMMIT must be set!"
fi

INITIAL_DIR="${PWD}"
WORK_DIR=/tmp/docker_work_dir

mkdir "${WORK_DIR}"
cd "${WORK_DIR}"
wget --quiet https://storage.googleapis.com/pub/gsutil.tar.gz
tar xzf gsutil.tar.gz

python3 gsutil/gsutil cp "gs://${GCS_BUCKET}/*_${GRR_COMMIT}/travis_job_*server_deb/grr-server_*.tar.gz" .

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
