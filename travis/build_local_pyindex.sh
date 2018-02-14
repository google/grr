#!/bin/bash

set -e

function build_sdists() {
  if [[ -d sdists ]]; then
    echo "Removing existing sdists directory."
    rm -rf sdists
  fi

  python grr/proto/setup.py --quiet sdist \
      --formats=zip --dist-dir="${PWD}/sdists"
  python setup.py --quiet sdist --formats=zip \
      --dist-dir="${PWD}/sdists" --no-sync-artifacts
  python grr/client/setup.py --quiet sdist \
      --formats=zip --dist-dir="${PWD}/sdists"
  python api_client/python/setup.py --quiet sdist \
      --formats=zip --dist-dir="${PWD}/sdists"
  python grr/config/grr-response-server/setup.py --quiet sdist \
      --formats=zip --dist-dir="${PWD}/sdists"
  python grr/config/grr-response-test/setup.py --quiet sdist \
      --formats=zip --dist-dir="${PWD}/sdists"
  python grr/config/grr-response-templates/setup.py sdist \
      --formats=zip --dist-dir="${PWD}/sdists"
}

function download_packages() {
  if [[ -d local_pypi ]]; then
    echo "Removing existing local_pypi directory."
    rm -rf local_pypi
  fi

  pip download --dest=local_pypi sdists/grr-response-proto-*.zip
  pip download --dest=local_pypi sdists/grr-response-core-*.zip
  pip download --find-links=sdists --dest=local_pypi sdists/grr-response-client-*.zip
  pip download --find-links=sdists --dest=local_pypi sdists/grr-api-client-*.zip
  pip download --find-links=sdists --dest=local_pypi sdists/grr-response-server-*.zip
  pip download --find-links=sdists --dest=local_pypi sdists/grr-response-test-*.zip
  pip download --find-links=sdists --dest=local_pypi sdists/grr-response-templates-*.zip
}

source "${HOME}/INSTALL/bin/activate"
build_sdists
download_packages

# Reduce the size of the tarball that gets uploaded to GCS by
# deleting unnecessary files.
rm grr/config/grr-response-templates/templates/*.zip
