#!/bin/bash

# Install grr into a virtualenv

set -e

source "${HOME}/INSTALL/bin/activate"
pip install --upgrade pip wheel setuptools
pip install nodeenv
nodeenv -p --prebuilt
# Pull in changes to activate made by nodeenv
source "${HOME}/INSTALL/bin/activate"
pip install -e .
if [[ "$TRAVIS_OS_NAME" == "linux" ]]; then
  pip install -e grr/config/grr-response-server/
fi
pip install -e grr/config/grr-response-test/
pip install -e grr/config/grr-response-client/

python makefile.py
cd grr/artifacts && python makefile.py && cd -
