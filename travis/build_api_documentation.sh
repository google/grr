#!/bin/bash

if [[ $# -ne 2 ]]
  then
    echo "Usage: $0 <OPENAPI_JSON_PATH> <OPENAPI_DOCUMENTATION_PATH>"
    exit 1
fi

OPENAPI_JSON_PATH=$1
OPENAPI_DOCUMENTATION_PATH=$2

function setup_environment() {
  # Set up virtual python and node environment.
  python3 -m venv "${HOME}/DOCUMENTATION_VENV"
  source "${HOME}/DOCUMENTATION_VENV/bin/activate"
  pip3 install --upgrade pip wheel six setuptools nodeenv absl-py mysqlclient
  nodeenv -p --prebuilt --node=12.18.0
  source "${HOME}/DOCUMENTATION_VENV/bin/activate"

  # Install GRR pip packages from local pyindex.
  pip install --no-index --no-cache-dir --find-links=local_pypi \
    local_pypi/grr-response-proto-*.zip \
    local_pypi/grr-response-core-*.zip \
    local_pypi/grr-response-client-*.zip \
    local_pypi/grr-api-client-*.zip \
    local_pypi/grr-response-client-builder-*.zip \
    local_pypi/grr-response-server-*.zip
}

function generate_openapi_description() {
  python3 "travis/get_openapi_description.py" --local_json_path "$1"
}

function generate_documentation() {
  npx redoc-cli@0.9.12 bundle "$1"
  mkdir -p "$(dirname "$2")"
  mv "redoc-static.html" "$2"
}

setup_environment
generate_openapi_description "$OPENAPI_JSON_PATH"
generate_documentation "$OPENAPI_JSON_PATH" "$OPENAPI_DOCUMENTATION_PATH"

deactivate