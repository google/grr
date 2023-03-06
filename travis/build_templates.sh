#!/bin/bash

set -e

source "${HOME}/INSTALL/bin/activate"

grr_client_build build --output gcs_upload_dir

# We only have one template on linux or OS X so using *.zip is safe here
grr_client_build \
  --verbose \
  --secondary_configs grr/test/grr_response_test/test_data/dummyconfig.yaml \
  repack \
  --template gcs_upload_dir/*.zip \
  --output_dir gcs_upload_dir

# We don't install on linux because we're running on travis container
# infrastructure that doesn't allow for sudo (but has startup time and
# performance advantages). We upload the installers with the templates to cloud
# storage so it can be verified manually.
# TODO(user): we could possibly add another travis target with sudo:true that
# just waits for the installer to be available in a cloud storage bucket for the
# build, then installs it.
if [[ "$TRAVIS_OS_NAME" == "osx" ]]; then
  sudo installer -verbose -pkg gcs_upload_dir/*.pkg -target /
fi
