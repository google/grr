#!/bin/bash

# Install grr into a virtualenv

set -e

source "${HOME}/INSTALL/bin/activate"
pip install --upgrade pip wheel six setuptools nodeenv

# Install the latest version of nodejs. Some packages
# may not be compatible with the version.
# nodeenv -p --prebuilt

# This is a temporary hack to un-break the Travis
# build.
#
# TODO(user): Stop doing this after a node-sass
# binary that supports node 8.0.0 is available.
#
# See https://github.com/sass/node-sass/pull/1969
nodeenv -p --prebuilt --node=7.10.0

# Pull in changes to activate made by nodeenv
source "${HOME}/INSTALL/bin/activate"

# Set default value for PROTOC if necessary.
default_protoc_path="${HOME}/protobuf/bin/protoc"
if [[ -z "${PROTOC}" && "${PATH}" != *'protoc'* && -f "${default_protoc_path}" ]]; then
  echo "PROTOC is not set. Will set it to ${default_protoc_path}."
  export PROTOC="${default_protoc_path}"
fi

# Get around a Travis bug: https://github.com/travis-ci/travis-ci/issues/8315#issuecomment-327951718
unset _JAVA_OPTIONS

# Install grr packages as links pointing to code in the
# checked-out repository.
# Note that because of dependencies, order here is important.
#
# Proto package.
pip install -e grr/proto

# Base package, grr-response-core, depends on grr-response-proto.
pip install -e grr/core

# Depends on grr-response-core
pip install -e grr/client

# Depends on grr-response-core
pip install -e api_client/python

# Depends on grr-response-client
pip install -e grr/server/[mysqldatastore]

# Depends on grr-response-server and grr-api-client
pip install -e grr/test

cd grr/proto && python makefile.py && cd -
cd grr/core/grr_response_core/artifacts && python makefile.py && cd -
