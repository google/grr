#!/bin/bash

# Install grr into a virtualenv

set -e

source "${HOME}/INSTALL/bin/activate"
pip install --upgrade pip wheel six setuptools

# Set default value for PROTOC if necessary.
default_protoc_path="${HOME}/protobuf/bin/protoc"
if [[ -z "${PROTOC}" && "${PATH}" != *'protoc'* && -f "${default_protoc_path}" ]]; then
  echo "PROTOC is not set. Will set it to ${default_protoc_path}."
  export PROTOC="${default_protoc_path}"
fi

# Get around a Travis bug: https://github.com/travis-ci/travis-ci/issues/8315#issuecomment-327951718
unset _JAVA_OPTIONS

# Install GRR packages.
# Note that because of dependencies, order here is important.
# ===========================================================

# Proto package.
cd grr/proto
python setup.py sdist
pip install ./dist/grr-response-proto-*.tar.gz
cd -

# Base package, grr-response-core, depends on grr-response-proto.
# Running sdist first since it accepts --no-sync-artifacts and
# --no-make-ui-files flags.
python setup.py sdist --no-sync-artifacts --no-make-ui-files
pip install ./dist/grr-response-core-*.tar.gz

# Depends on grr-response-core.
# Note that we can't do "python setup.py install" since setup.py
# is configured to include version.ini as data and version.ini
# only gets copied during sdist step.
cd grr/config/grr-response-client
python setup.py sdist
pip install ./dist/grr-response-client-*.tar.gz
cd -

