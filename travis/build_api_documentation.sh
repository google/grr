#!/bin/bash

# TODO: Delete debug commands below
pwd
ls -ltr .
ls -ltr grr/local_pypi
ls -ltr
tree -L 2
# TODO: Delete above

function setup_environment() {
  # Set up virtual python and node environment.
  python3 -m venv "${HOME}/DOCUMENTATION_VENV"
  source "${HOME}/DOCUMENTATION_VENV/activate"
  nodeenv -p --prebuilt --node=12.18.0
  source "${HOME}/DOCUMENTATION_VENV/activate"

  # Install GRR pip packages from local pyindex.
  pip install --no-index --no-cache-dir --find-links=grr/local_pypi \
    grr/local_pypi/grr-response-proto-*.zip \
    grr/local_pypi/grr-response-core-*.zip \
    grr/local_pypi/grr-response-client-*.zip \
    grr/local_pypi/grr-api-client-*.zip \
    grr/local_pypi/grr-response-server-*.zip
}

function generate_openapi_description() {
  "${HOME}/DOCUMENTATION_VENV/bin/python" "travis/get_openapi_description.py"
}

function generate_documentation() {
  npx redoc-cli@0.9.12 bundle "${HOME}/${OPENAPI_JSON_FOLDER_NAME}/${OPENAPI_JSON_FILE_NAME}"
  mkdir "${HOME}/${OPENAPI_DOCUMENTATION_FOLDER_NAME}"
  mv "redoc-static.html" "${HOME}/${OPENAPI_DOCUMENTATION_FOLDER_NAME}/${OPENAPI_DOCUMENTATION_FILE_NAME}"
}

setup_environment
generate_openapi_description
generate_documentation
