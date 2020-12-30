#!/bin/bash

set -ex

readonly GRR_PKGS=(\
  'grr-response-proto' \
  'grr-response-core' \
  'grr-response-client' \
  'grr-response-client-builder' \
  'grr-api-client' \
  'grr-response-server' \
  'grr-response-test' \
  'grr-response-templates' \
  'grr-colab' \
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
  python grr/core/setup.py --quiet sdist --formats=zip \
      --dist-dir="${PWD}/sdists" --no-sync-artifacts
  python grr/client/setup.py --quiet sdist \
      --formats=zip --dist-dir="${PWD}/sdists"
  python grr/client_builder/setup.py --quiet sdist \
      --formats=zip --dist-dir="${PWD}/sdists"
  python api_client/python/setup.py --quiet sdist \
      --formats=zip --dist-dir="${PWD}/sdists"
  python grr/server/setup.py --quiet sdist \
      --formats=zip --dist-dir="${PWD}/sdists"
  python grr/test/setup.py --quiet sdist \
      --formats=zip --dist-dir="${PWD}/sdists"
  python grr/config/grr_response_templates/setup.py sdist \
      --formats=zip --dist-dir="${PWD}/sdists"
  python colab/setup.py --quiet sdist \
      --formats=zip --dist-dir="${PWD}/sdists"
}

function download_packages() {
  if [[ -d local_pypi ]]; then
    echo "Removing existing local_pypi directory."
    rm -rf local_pypi
  fi

  # Get the name of a file in the sdists directory.
  first_sdist="$(ls sdists | sort | head -1)"
  # Truncate the name of the package from the filename; for instance,
  # 'grr-api-client-3.2.4.post9.zip' becomes '3.2.4.post9.zip'.
  version_extension="${first_sdist##*-}"

  for pkg in "${GRR_PKGS[@]}"; do
    # shellcheck disable=SC2086
    pip download --find-links=sdists --dest=local_pypi "$(ls sdists/${pkg}-${version_extension})"
  done

  # Installation of the grr-response-test sdist from local_pypi will fail
  # if the version of idna needed by requests is not present.
  # See https://ci.appveyor.com/project/grr/grr/builds/20793753.
  pip download --find-links=local_pypi --dest=local_pypi idna==2.7

  # This is needed to build some of the wheels.
  pip download --find-links=local_pypi --dest=local_pypi wheel setuptools
}

function verify_packages() {
  for pkg in "${GRR_PKGS[@]}"; do
    pkg_regex="^${pkg}-[^\-]+\.zip$"
    # shellcheck disable=SC2086
    pkg_count="$(ls local_pypi | grep -P ${pkg_regex} 2>/dev/null | wc -l)"
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
rm -rf sdists
rm grr/config/grr_response_templates/templates/*.zip
