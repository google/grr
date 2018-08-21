#!/bin/bash
#
# This script downloads the most recent sdists for GRR and installs
# them in a Docker image.

set -e

INITIAL_DIR="${PWD}"
WORK_DIR=/tmp/docker_work_dir

pyscript="
import ConfigParser
config = ConfigParser.SafeConfigParser()
config.read('version.ini')
print('%s.%s.%s-%s' % (
    config.get('Version', 'major'),
    config.get('Version', 'minor'),
    config.get('Version', 'revision'),
    config.get('Version', 'release')))
"
readonly DEB_VERSION="$(python -c "${pyscript}")"
wget --quiet "https://storage.googleapis.com/autobuilds.grr-response.com/_latest_server_deb/grr-server_${DEB_VERSION}.tar.gz"

tar xzf grr-server_*.tar.gz

$GRR_VENV/bin/pip install --no-index --no-cache-dir \
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
