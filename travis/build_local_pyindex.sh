#!/bin/bash

set -e

readonly GRR_PKGS=(\
  'grr-response-proto' \
  'grr-response-core' \
  'grr-response-client' \
  'grr-api-client' \
  'grr-response-server' \
  'grr-response-test' \
  'grr-response-templates' \
)

function fatal() {
  >&2 echo "Error: ${1}"
  exit 1
}

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
  python grr/test/setup.py --quiet sdist \
      --formats=zip --dist-dir="${PWD}/sdists"
  python grr/config/grr-response-templates/setup.py sdist \
      --formats=zip --dist-dir="${PWD}/sdists"
}

function download_packages() {
  if [[ -d local_pypi ]]; then
    echo "Removing existing local_pypi directory."
    rm -rf local_pypi
  fi

  for pkg in "${GRR_PKGS[@]}"; do
    # shellcheck disable=SC2086
    pip download --find-links=sdists --dest=local_pypi "$(ls sdists/${pkg}-*.zip)"
  done

  # See https://github.com/google/rekall/issues/422
  #
  # Installation of the grr-response-test sdist from local_pypi will fail
  # if the version of sortedcontainers needed by Rekall is not present.
  #
  # TODO(user): This won't be necessary once the github issue is fixed.
  pip download --find-links=local_pypi --dest=local_pypi sortedcontainers==1.5.7
}

function verify_packages() {
  for pkg in "${GRR_PKGS[@]}"; do
    # shellcheck disable=SC2086
    pkg_count="$(ls local_pypi/${pkg}-* 2>/dev/null | wc -l)"
    if [[ "${pkg_count}" -eq 0 ]]; then
      fatal "Failed to find sdist for ${pkg} in local_pypi."
    elif [[ "${pkg_count}" -gt 1 ]]; then
      fatal "Found multiple versions for ${pkg} in local_pypi."
    fi
    # shellcheck disable=SC2086
    actual_sum=($(md5sum local_pypi/${pkg}-*.zip))
    # shellcheck disable=SC2086
    expected_sum=($(md5sum sdists/${pkg}-*.zip))
    if [[ "${actual_sum[0]}" != "${expected_sum[0]}" ]]; then
      fatal "sdist for ${pkg} in local_pypi is different from the sdist that has just been built."
    fi
  done
}

source "${HOME}/INSTALL/bin/activate"
build_sdists
download_packages
verify_packages

# Reduce the size of the tarball that gets uploaded to GCS by
# deleting unnecessary files.
rm grr/config/grr-response-templates/templates/*.zip
