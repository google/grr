#!/bin/bash

# Build client templates and upload them to cloud storage.
#
# This script must be run inside travis, as it relies on some travis specific
# environment variables. Ideally it should run in the travis deploy stage rather
# than the script phase (which will run for every pull request), but here is a
# litany of reasons why it doesn't.
#
# There is already a travis gcs deployer but it isn't usable:
# https://github.com/travis-ci/dpl/issues/476
#
# When using the experimental script deployer there were differences between the
# virtual env in the deploy and install stages that caused the client build to
# fail (previously installed grr-* packages would somehow be missing from the
# virtualenv). I'm still attempting to make a minimal reproducible case for a
# good bug report there.
#
# and it's also annoying to debug:
# https://github.com/travis-ci/dpl/issues/477
#
# We could use after_success but it doesn't exit on error:
# https://github.com/travis-ci/travis-ci/issues/758

set -e

source "${HOME}/INSTALL/bin/activate"

# Temporary workaround until we migrate off PackageMaker.
if [[ "$TRAVIS_OS_NAME" == "osx" ]]; then
  cd /Applications
  wget -q https://storage.googleapis.com/grr-osx-buildtools/packagemaker.tar.gz
  tar zxf packagemaker.tar.gz
  cd -
fi

grr_client_build build --output built_templates
grr_client_build build_components --output built_templates

# If we don't have the sdk, go get it. While we could cache the cloud sdk
# directory it may contain authentication tokens after the authorization step
# below, so we don't.
gcloud version || ( wget -q https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-sdk-116.0.0-linux-x86_64.tar.gz && tar zxf google-cloud-sdk-116.0.0-linux-x86_64.tar.gz -C "${HOME}" )

# See https://docs.travis-ci.com/user/encrypting-files/
openssl aes-256-cbc -K "$encrypted_db009a5a71c6_key" \
  -iv "$encrypted_db009a5a71c6_iv" \
  -in travis/travis_uploader_service_account.json.enc \
  -out travis/travis_uploader_service_account.json -d

gcloud auth activate-service-account --key-file travis/travis_uploader_service_account.json
echo Uploading templates to "gs://autobuilds.grr-response.com/${TRAVIS_JOB_NUMBER}"
gsutil -m cp built_templates/* "gs://autobuilds.grr-response.com/${TRAVIS_JOB_NUMBER}/"

if [[ "$TRAVIS_OS_NAME" == "linux" ]]; then
  shred -u travis/travis_uploader_service_account.json
fi
if [[ "$TRAVIS_OS_NAME" == "osx" ]]; then
  srm -sz travis/travis_uploader_service_account.json
fi
