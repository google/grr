#!/bin/bash
#
# Installs the grr-response-client-builder package from source into a
# virtualenv.

set -e

pip install --upgrade pip wheel six setuptools

# Install GRR packages.
# Note that because of dependencies, order here is important.
# ===========================================================

# Proto package.
cd grr/proto
python setup.py sdist
pip install ./dist/grr-response-proto-*.tar.gz
cd -

# Base package, grr-response-core, depends on grr-response-proto.
# Running sdist first since it accepts --no-sync-artifacts flag.
cd grr/core
python setup.py sdist --no-sync-artifacts
pip install ./dist/grr-response-core-*.tar.gz
cd -

# Depends on grr-response-core.
# Note that we can't do "python setup.py install" since setup.py
# is configured to include version.ini as data and version.ini
# only gets copied during sdist step.
cd grr/client
python setup.py sdist
pip install ./dist/grr-response-client-*.tar.gz
cd -

# Depends on grr-response-client.
# Note that we can't do "python setup.py install" since setup.py
# is configured to include version.ini as data and version.ini
# only gets copied during sdist step.
cd grr/client_builder
python setup.py sdist
pip install ./dist/grr-response-client-builder-*.tar.gz
cd -
