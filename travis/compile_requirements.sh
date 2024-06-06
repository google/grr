#!/bin/bash
#

set -ex

OS=$1

DIR="$(dirname "$(which "$0")")"

CURRENT_REQUIREMENTS="$DIR/requirements/$OS.txt"

OUT_FOLDER="requirements"
mkdir "$OUT_FOLDER"
OUT_FILE="$OUT_FOLDER/$OS.txt"

pip install --require-hashes -r "$DIR/base_tooling_requirements.txt"

if [ $OS = "osx" ]
then
	pip-compile --generate-hashes -o "$OUT_FILE" \
		"$DIR/../api_client/python/requirements.in" \
		"$DIR/../grr/core/requirements.in" \
		"$DIR/../grr/server/requirements.in" \
		"$DIR/../grr/proto/requirements.in" \
		"$DIR/../grr/client/requirements.in" \
		"$DIR/../grr/client/requirements_osx.in" \
		"$DIR/../grr/client_builder/requirements.in" \
		"$DIR/../grr/test/requirements.in"
elif [ $OS = "ubuntu" ]
then
	pip-compile --generate-hashes -o "$OUT_FILE" \
		"$DIR/../api_client/python/requirements.in" \
		"$DIR/../grr/core/requirements.in" \
		"$DIR/../grr/server/requirements.in" \
		"$DIR/../grr/server/requirements_ubuntu.in" \
		"$DIR/../grr/proto/requirements.in" \
		"$DIR/../grr/client/requirements.in" \
		"$DIR/../grr/client/requirements_ubuntu.in" \
		"$DIR/../grr/client_builder/requirements.in" \
		"$DIR/../grr/test/requirements.in"
else
	pip-compile --generate-hashes -o "$OUT_FILE" \
		"$DIR/../api_client/python/requirements.in" \
		"$DIR/../grr/core/requirements.in" \
		"$DIR/../grr/server/requirements.in" \
		"$DIR/../grr/proto/requirements.in" \
		"$DIR/../grr/client/requirements.in" \
		"$DIR/../grr/client_builder/requirements.in" \
		"$DIR/../grr/test/requirements.in"
fi
