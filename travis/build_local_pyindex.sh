#!/bin/bash

set -ex

readonly GRR_PKGS=(
  'grr_response_proto'
  'grr_response_core'
  'grr_response_client'
  'grr_response_client_builder'
  'grr_api_client'
  'grr_response_server'
  'grr_response_test'
  'grr_response_templates'
  'grr_colab'
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

  pip install --upgrade pip setuptools wheel build

  python -m build --sdist --outdir "${PWD}/sdists" grr/proto
  python -m build --sdist --no-isolation --outdir "${PWD}/sdists" grr/core
  python -m build --sdist --outdir "${PWD}/sdists" grr/client
  python -m build --sdist --no-isolation --outdir "${PWD}/sdists" \
    grr/client_builder
  python -m build --sdist --no-isolation --outdir "${PWD}/sdists" \
    api_client/python
  python -m build --sdist --no-isolation --outdir "${PWD}/sdists" grr/server
  python -m build --sdist --no-isolation --outdir "${PWD}/sdists" grr/test
  python -m build --sdist --no-isolation --outdir "${PWD}/sdists" \
    grr/config/grr_response_templates
  python -m build --sdist --no-isolation --outdir "${PWD}/sdists" colab
}

function download_packages() {
  if [[ -d local_pypi ]]; then
    echo "Removing existing local_pypi directory."
    rm -rf local_pypi
  fi

  # Get the name of a file in the sdists directory.
  first_sdist="$(ls sdists | sort | head -1)"
  # Truncate the name of the package from the filename; for instance,
  # 'grr_api_client-3.2.4.post9.tar.gz' becomes '3.2.4.post9.tar.gz'.
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

  pip download --find-links=local_pypi --dest=local_pypi wheel setuptools Cython \
    grpcio==1.78.0 grpcio-tools==1.78.0 protobuf==6.33.6

}

function verify_packages() {
  for pkg in "${GRR_PKGS[@]}"; do
    pkg_regex="^${pkg}-[^\-]+\.tar\.gz$"
    # shellcheck disable=SC2086
    pkg_count="$(ls local_pypi | grep -P ${pkg_regex} 2>/dev/null | wc -l)"
    if [[ "${pkg_count}" -eq 0 ]]; then
      fatal "Failed to find sdist for ${pkg} in local_pypi."
    elif [[ "${pkg_count}" -gt 1 ]]; then
      fatal "Found multiple versions for ${pkg} in local_pypi."
    fi
    # shellcheck disable=SC2086
    actual_sum=($(md5sum local_pypi/${pkg}-*.tar.gz))
    # shellcheck disable=SC2086
    expected_sum=($(md5sum sdists/${pkg}-*.tar.gz))
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
