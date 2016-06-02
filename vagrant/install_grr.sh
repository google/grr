#!/bin/bash

# This script installs a fresh copy of GRR from source, you need to run
# install_[darwin|linux].sh first.

set -e
set -x

function install() {
  BUILDDIR="${HOME}/grrbuild"
  rm -rf "${BUILDDIR}" && mkdir "${BUILDDIR}"

  /usr/local/bin/virtualenv -p /usr/local/bin/python2.7 "${BUILDDIR}/PYTHON_ENV"
  source "${BUILDDIR}/PYTHON_ENV/bin/activate"
  # pip takes a copy of the whole src tree, which includes the vagrant dir, so
  # it continues copying until it runs out of space. The workaround is to build
  # an sdist and install that.
  # https://github.com/google/grr/issues/373
  cd /grr
  python setup.py sdist --dist-dir="${BUILDDIR}/core" --no-make-docs --no-sync-artifacts
  cd -
  cd /grr/grr/config/grr-response-client/
  python setup.py sdist --dist-dir="${BUILDDIR}/client"
  cd -

  cd "${BUILDDIR}"
  pip install core/*.tar.gz
  pip install client/*.tar.gz
  cd -

  # pyinstaller fails to include protobuf because there is no __init__.py:
  # https://github.com/google/protobuf/issues/713
  touch "${BUILDDIR}/PYTHON_ENV/lib/python2.7/site-packages/google/__init__.py"
}

install
