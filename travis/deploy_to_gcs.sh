#!/bin/bash

set -e

commit_timestamp_secs="$(git show -s --format=%ct "${TRAVIS_COMMIT}")"

# Hacky, but platform independent way of formatting the timestamp.
pyscript="
from datetime import datetime
print(datetime.utcfromtimestamp(
    ${commit_timestamp_secs}).strftime('%Y-%m-%dT%H:%MUTC'));
"
commit_timestamp=$(python -c "${pyscript}")

gcs_dest="gs://${GCS_BUCKET}/${commit_timestamp}_${TRAVIS_COMMIT}/travis_job_${TRAVIS_JOB_NUMBER}_${GCS_TAG}/"

echo Uploading templates to "${gcs_dest}"
gsutil -m cp gcs_upload_dir/* "${gcs_dest}"

if [[ "$TRAVIS_OS_NAME" == "linux" ]]; then
  shred -u travis/travis_uploader_service_account.json
fi
if [[ "$TRAVIS_OS_NAME" == "osx" ]]; then
  srm -sz travis/travis_uploader_service_account.json
fi
