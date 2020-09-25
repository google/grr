#!/bin/bash

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
  python3 "travis/get_openapi_description.py"
}

function generate_documentation() {
  npx redoc-cli@0.9.12 bundle "${HOME}/${OPENAPI_JSON_FOLDER_NAME}/${OPENAPI_JSON_FILE_NAME}"
  mkdir "${HOME}/${OPENAPI_DOCUMENTATION_FOLDER_NAME}"
  mv "redoc-static.html" "${HOME}/${OPENAPI_DOCUMENTATION_FOLDER_NAME}/${OPENAPI_DOCUMENTATION_FILE_NAME}"
}

setup_environment
generate_openapi_description
generate_documentation

deactivate
