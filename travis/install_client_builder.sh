#!/bin/bash
#
# Installs the grr-response-client-builder package from source into a
# virtualenv.

set -e

source "${HOME}/INSTALL/bin/activate"
pip install -r build_requirements.txt

# Get around a Travis bug: https://github.com/travis-ci/travis-ci/issues/8315#issuecomment-327951718
unset _JAVA_OPTIONS

# Install GRR packages.
# Note that because of dependencies, order here is important.
# ===========================================================

# Proto package.
pip install ./grr/proto

# Base package, grr-response-core, depends on grr-response-proto.
pip install ./grr/core

# Depends on grr-response-core.
pip install ./grr/client

# Depends on grr-response-client.
pip install ./grr/client_builder
