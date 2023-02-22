#!/bin/bash

# Install grr into a virtualenv

set -ex

source "${HOME}/INSTALL/bin/activate"
pip install --upgrade pip wheel six setuptools nodeenv

# Install the latest version of nodejs. Some packages
# may not be compatible with the version.
nodeenv -p --prebuilt --node=16.13.0

# Pull in changes to activate made by nodeenv
source "${HOME}/INSTALL/bin/activate"

# Get around a Travis bug: https://github.com/travis-ci/travis-ci/issues/8315#issuecomment-327951718
unset _JAVA_OPTIONS

# This causes 'gulp compile' to fail.
unset JAVA_TOOL_OPTIONS

# Install grr packages as links pointing to code in the
# checked-out repository.
# Note that because of dependencies, order here is important.
#
# Proto package.
pip install -e grr/proto --progress-bar off

# Depends on grr-response-proto
pip install -e grr/core --progress-bar off

# Depends on grr-response-core
pip install -e grr/client --progress-bar off

# Depends on grr-response-core
pip install -e api_client/python --progress-bar off

# Depends on grr-response-client
pip install -e grr/client_builder --progress-bar off

# Depends on grr-response-client-builder
pip install -e grr/server/[mysqldatastore] --progress-bar off

# Depends on grr-api-client and grr-response-proto
pip install -e colab --progress-bar off

# Depends on all other packages
pip install -e grr/test --progress-bar off

cd grr/proto && python makefile.py && cd -
cd grr/core/grr_response_core/artifacts && python makefile.py && cd -
