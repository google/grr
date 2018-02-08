#!/bin/bash
#
# Script that uploads artifacts built by Travis to GCS.

set -e

function delete_gcs_keys() {
  if [[ "$TRAVIS_OS_NAME" == "linux" ]]; then
    shred -u travis/travis_uploader_service_account.json
  elif [[ "$TRAVIS_OS_NAME" == "osx" ]]; then
    rm -P travis/travis_uploader_service_account.json
  fi
}

commit_timestamp_secs="$(git show -s --format=%ct "${TRAVIS_COMMIT}")"

# Hacky, but platform independent way of formatting the timestamp.
pyscript="
from datetime import datetime
print(datetime.utcfromtimestamp(
    ${commit_timestamp_secs}).strftime('%Y-%m-%dT%H:%MUTC'));
"
commit_timestamp=$(python -c "${pyscript}")

gcs_dest="gs://${GCS_BUCKET}/${commit_timestamp}_${TRAVIS_COMMIT}/travis_job_${TRAVIS_JOB_NUMBER}_${GCS_TAG}"

echo Uploading templates to "${gcs_dest}"
gsutil -m cp gcs_upload_dir/* "${gcs_dest}"

# No more work to do if the currently-running job is not the one that builds
# server debs.
if [[ "${GCS_TAG}" != 'server_deb' ]]; then
  delete_gcs_keys
  exit 0
fi

latest_dir="gs://${GCS_BUCKET}/_latest_server_deb"
backup_dir="gs://${GCS_BUCKET}/.latest_server_deb"

# Copy the server deb to its backup location.
original_deb_exists="$( ( gsutil --quiet stat "${gcs_dest}/*.deb" && echo true ) || echo false )"
if [[ "${original_deb_exists}" != 'true' ]]; then
  echo "Server deb not found in ${gcs_dest}"
  delete_gcs_keys
  exit 1
fi
gsutil rm -r "${backup_dir}" || true
gsutil -m cp "${gcs_dest}/*" "${backup_dir}"

# Copy the server deb from its backup location to its expected location.
backup_deb_exists="$( ( gsutil --quiet stat "${backup_dir}/*.deb" && echo true ) || echo false )"
if [[ "${backup_deb_exists}" != 'true' ]]; then
  echo "Server deb not found in ${backup_dir}"
  delete_gcs_keys
  exit 2
fi
gsutil rm -r "${latest_dir}" || true
gsutil -m cp "${backup_dir}/*" "${latest_dir}"

delete_gcs_keys

# Trigger build of a new GRR Docker image (grrdocker/grr)
# See https://hub.docker.com/r/grrdocker/grr/~/settings/automated-builds/
curl -H "Content-Type: application/json" --data '{"docker_tag": "latest"}' -X POST https://registry.hub.docker.com/u/grrdocker/grr/trigger/4499c4d4-4a8b-48da-bc95-5dbab39be545/
