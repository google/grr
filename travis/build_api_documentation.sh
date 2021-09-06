#!/bin/bash

set -ex

if [[ $# -ne 2 ]]
  then
    echo "Usage: $0 <OPENAPI_JSON_PATH> <OPENAPI_DOCUMENTATION_PATH>"
    exit 1
fi

OPENAPI_JSON_PATH=$1
OPENAPI_DOCUMENTATION_PATH=$2

function generate_openapi_description() {
  python3 "travis/get_openapi_description.py" --local_json_path "$1"
}

function generate_documentation() {
  npx redoc-cli@0.12.3 bundle "$1"
  mv "redoc-static.html" "$2"
}

generate_openapi_description "$OPENAPI_JSON_PATH"
generate_documentation "$OPENAPI_JSON_PATH" "$OPENAPI_DOCUMENTATION_PATH"
