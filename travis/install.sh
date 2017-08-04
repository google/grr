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

# Install grr packages as links pointing to code in the
# checked-out repository.
# Note that because of dependencies, order here is important.
#
# Base package, grr-response-core
pip install -e .

# Depends on grr-response-core
pip install -e grr/config/grr-response-client/

# Depends on grr-response-core
pip install -e api_client/python/

# Depends on grr-response-client
pip install -e grr/config/grr-response-server/

# Depends on grr-response-server and grr-api-client
pip install -e grr/config/grr-response-test/

python makefile.py
cd grr/artifacts && python makefile.py && cd -
