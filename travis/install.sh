#!/bin/bash

# Install grr into a virtualenv

set -e

source "${HOME}/INSTALL/bin/activate"
pip install --upgrade pip wheel setuptools
pip install nodeenv

# Install the latest version of nodejs. Some packages
# may not be compatible with the version.
nodeenv -p --prebuilt

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
pip install -e .
if [[ "$TRAVIS_OS_NAME" == "linux" || "$TRAVIS_OS_NAME" == "osx" ]]; then
  pip install -e grr/config/grr-response-server/
fi
pip install -e api_client/python/
pip install -e grr/config/grr-response-test/
pip install -e grr/config/grr-response-client/

python makefile.py
cd grr/artifacts && python makefile.py && cd -
