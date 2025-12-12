#!/bin/bash

# Install grr into a virtualenv

set -ex

source "${HOME}/INSTALL/bin/activate"
# Limiting setuptools version due to
# https://github.com/pypa/setuptools/issues/3278
# (it behaves incorrectly on Ubuntu 22 on virtualenvs with access to
# globally installed packages).
pip install --upgrade 'pip<23.1' wheel six 'setuptools<58.3.1' nodeenv

# Install the latest version of nodejs. Some packages
# may not be compatible with the version.
nodeenv -p --prebuilt --node=22.14.0

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
pip install --no-use-pep517 -e grr/proto --progress-bar off

# Depends on grr-response-proto
pip install --no-use-pep517 -e grr/core --progress-bar off

# Depends on grr-response-core
pip install --no-use-pep517 -e grr/client --progress-bar off

# Depends on grr-response-core
pip install --no-use-pep517 -e api_client/python --progress-bar off

# Depends on grr-response-client
pip install --no-use-pep517 -e grr/client_builder --progress-bar off

# Depends on grr-response-client-builder
pip install --no-use-pep517 -e grr/server --progress-bar off

# Depends on grr-api-client and grr-response-proto
pip install --no-use-pep517 -e colab --progress-bar off

# Depends on all other packages
pip install --no-use-pep517 -e grr/test --progress-bar off

cd grr/proto && python makefile.py && cd -
cd grr/core/grr_response_core/artifacts && python makefile.py && cd -
