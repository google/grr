#!/usr/bin/env python
# python3
"""Tool used by Travis to upload build artifacts to the Google Cloud.

This tool also triggers Appveyor builds for certain Travis jobs after
results are uploaded.
"""
import datetime
import os
import shutil
import subprocess
import tempfile

from absl import app
from absl import flags
from absl import logging
import requests

from google.cloud import storage

flags.DEFINE_string("encrypted_service_key", "",
                    "Path to Travis's GCP service account key.")
flags.DEFINE_string("build_results_dir", "",
                    "Path to the local directory containing build results.")
flags.DEFINE_string(
    "openapi_json_dir", "",
    "Path to the local directory containing the generated "
    "OpenAPI description JSON.")
flags.DEFINE_string(
    "openapi_docs_dir", "",
    "Path to the local directory containing the generated "
    "documentation HTML.")

# Environment variables.
_TRAVIS_COMMIT = "TRAVIS_COMMIT"
_TRAVIS_BRANCH = "TRAVIS_BRANCH"
_TRAVIS_JOB_NUMBER = "TRAVIS_JOB_NUMBER"
_SERVICE_FILE_ENCRYPTION_KEY_VAR = "SERVICE_FILE_ENCRYPTION_KEY_VAR"
_SERVICE_FILE_ENCRYPTION_IV_VAR = "SERVICE_FILE_ENCRYPTION_IV_VAR"
_GCS_BUCKET = "GCS_BUCKET"
_GCS_BUCKET_OPENAPI = "GCS_BUCKET_OPENAPI"
_GCS_TAG = "GCS_TAG"
_APPVEYOR_ACCOUNT_NAME = "APPVEYOR_ACCOUNT_NAME"
_APPVEYOR_TOKEN = "APPVEYOR_TOKEN"
_APPVEYOR_WINDOWS_TEMPLATES_SLUG = "APPVEYOR_WINDOWS_TEMPLATES_SLUG"
_APPVEYOR_E2E_TESTS_SLUG = "APPVEYOR_E2E_TESTS_SLUG"
_APPVEYOR_DOCKER_BUILD_SLUG = "APPVEYOR_DOCKER_BUILD_SLUG"

# Other constants.
_DECRYPTED_SERVICE_FILE_NAME = "travis_uploader_service_account.json"
_GCS_BUCKET_TIME_FORMAT = "%Y-%m-%dT%H:%MUTC"
_UBUNTU_64BIT_TAG = "ubuntu_64bit"
_SERVER_DEB_TAG = "server_deb"
_APPVEYOR_API_URL = "https://ci.appveyor.com/api/builds"
_REDACTED_SECRET_PLACEHOLDER = "**REDACTED SECRET**"
_LATEST_SERVER_DEB_GCS_DIR = "_latest_server_deb"


class DecryptionError(Exception):
  """Raised when a problem occurs when trying to decrypt the GCP key."""


class AppveyorError(Exception):
  """Raised when a problem occurs when trying to communicate with Appveyor."""


class GCSUploadError(Exception):
  """Generic exception raised when an error occurs during upload of results."""


def _GetRedactedExceptionMessage(exception: Exception) -> str:
  """Returns the message for an exception after redacting sensitive info."""
  service_file_encryption_key_var = os.environ[_SERVICE_FILE_ENCRYPTION_KEY_VAR]
  service_file_encryption_iv_var = os.environ[_SERVICE_FILE_ENCRYPTION_IV_VAR]
  original_message = str(exception)
  redacted_message = original_message.replace(os.environ[_APPVEYOR_TOKEN],
                                              _REDACTED_SECRET_PLACEHOLDER)
  redacted_message = redacted_message.replace(
      os.environ[service_file_encryption_key_var], _REDACTED_SECRET_PLACEHOLDER)
  redacted_message = redacted_message.replace(
      os.environ[service_file_encryption_iv_var], _REDACTED_SECRET_PLACEHOLDER)
  return redacted_message


def _GetGCSBuildResultsDir() -> str:
  """Returns the GCS blob prefix for build results."""
  git_output = subprocess.check_output(
      ["git", "show", "-s", "--format=%ct", os.environ[_TRAVIS_COMMIT]])
  try:
    commit_timestamp = int(git_output.decode("utf-8").strip())
  except ValueError:
    raise ValueError(f"Received invalid response from git: {git_output}.")
  formatted_commit_timestamp = datetime.datetime.utcfromtimestamp(
      commit_timestamp).strftime(_GCS_BUCKET_TIME_FORMAT)
  destination_dir = (
      f"{formatted_commit_timestamp}_{os.environ[_TRAVIS_COMMIT]}/"
      f"travis_job_{os.environ[_TRAVIS_JOB_NUMBER]}_{os.environ[_GCS_TAG]}")
  return destination_dir


def _DecryptGCPServiceFileTo(service_file_path: str):
  """Decrypts Travis's GCP service account key to the given location.

  More information about decrypting files on Travis can be found in
  https://docs.travis-ci.com/user/encrypting-files/

  Args:
    service_file_path: Full path of the decrypted JSON file to generate.

  Raises:
    DecryptionError: If decryption fails.
  """
  key_var_name = os.environ[_SERVICE_FILE_ENCRYPTION_KEY_VAR]
  iv_var_name = os.environ[_SERVICE_FILE_ENCRYPTION_IV_VAR]
  try:
    # pyformat: disable
    subprocess.check_call([
        "openssl", "aes-256-cbc",
        "-K", os.environ[key_var_name],
        "-iv", os.environ[iv_var_name],
        "-in", flags.FLAGS.encrypted_service_key,
        "-out", service_file_path,
        "-d",
    ])
    # pyformat: enable
  except Exception as e:
    redacted_message = _GetRedactedExceptionMessage(e)
    raise DecryptionError(
        f"{e.__class__.__name__} "
        f"encountered when trying to decrypt the GCP service key: "
        f"{redacted_message}")


def _UploadDirectory(local_dir: str, gcs_bucket: storage.Bucket, gcs_dir: str):
  """Upload the contents of a local directory to a GCS Bucket."""
  for file_name in os.listdir(local_dir):
    path = os.path.join(local_dir, file_name)
    if not os.path.isfile(path):
      logging.info("Skipping %s as it's not a file.", path)
      continue
    logging.info("Uploading: %s", path)
    gcs_blob = gcs_bucket.blob(f"{gcs_dir}/{file_name}")
    gcs_blob.upload_from_filename(path)


def _UploadBuildResults(gcs_bucket: storage.Bucket, gcs_build_results_dir: str):
  """Uploads all build results to Google Cloud Storage."""
  logging.info("Will upload build results to gs://%s/%s.",
               os.environ[_GCS_BUCKET], gcs_build_results_dir)

  _UploadDirectory(flags.FLAGS.build_results_dir, gcs_bucket,
                   gcs_build_results_dir)

  logging.info("GCS build results upload done.")


def _UploadOpenApiJson(gcs_bucket: storage.Bucket, gcs_openapi_dir: str):
  """Uploads the generated OpenAPI description JSON to Google Cloud Storage."""
  logging.info("Will upload generated OpenAPI JSON to gs://%s/%s.",
               os.environ[_GCS_BUCKET_OPENAPI], gcs_openapi_dir)

  _UploadDirectory(flags.FLAGS.openapi_json_dir, gcs_bucket, gcs_openapi_dir)

  logging.info("GCS OpenAPI JSON upload done.")


def _UploadDocumentation(gcs_bucket: storage.Bucket, gcs_docs_dir: str):
  """Uploads the generated GRR API documentation to Google Cloud Storage."""
  logging.info("Will upload generated GRR API documentation to gs://%s/%s.",
               os.environ[_GCS_BUCKET_OPENAPI], gcs_docs_dir)

  _UploadDirectory(flags.FLAGS.openapi_docs_dir, gcs_bucket, gcs_docs_dir)

  logging.info("GCS GRR API documentation upload done.")


def _TriggerAppveyorBuild(project_slug_var_name: str):
  """Sends a POST request to trigger an Appveyor build.

  Args:
    project_slug_var_name: The name of an environment variable containing an
      identifier for the Appveyor job to trigger.

  Raises:
    AppveyorError: If the trigger attempt is not successful.
  """
  data = {
      "accountName": os.environ[_APPVEYOR_ACCOUNT_NAME],
      "projectSlug": os.environ[project_slug_var_name],
      "branch": os.environ[_TRAVIS_BRANCH],
      "commitId": os.environ[_TRAVIS_COMMIT],
  }
  logging.info("Will trigger Appveyor build with params: %s", data)
  headers = {"Authorization": f"Bearer {os.environ[_APPVEYOR_TOKEN]}"}
  try:
    response = requests.post(_APPVEYOR_API_URL, json=data, headers=headers)
  except Exception as e:
    redacted_message = _GetRedactedExceptionMessage(e)
    raise AppveyorError(
        f"{e.__class__.__name__} encountered on POST request: {redacted_message}"
    )
  if not response.ok:
    raise AppveyorError(f"Failed to trigger Appveyor build; got response "
                        f"{response.status_code}.")


def _UpdateLatestServerDebDirectory(gcs_bucket: storage.Bucket,
                                    gcs_build_results_dir: str):
  """Updates the '_latest_server_deb' GCS directory with the latest results."""
  logging.info("Updating latest server deb directory.")

  old_build_results = list(
      gcs_bucket.list_blobs(prefix=_LATEST_SERVER_DEB_GCS_DIR))
  new_build_results = list(gcs_bucket.list_blobs(prefix=gcs_build_results_dir))
  if not new_build_results:
    raise GCSUploadError(
        "Failed to find build results for the server-deb Travis job.")

  for gcs_blob in old_build_results:
    logging.info("Deleting previous blob: %s", gcs_blob)
    gcs_blob.delete()

  for gcs_blob in new_build_results:
    build_result_filename = gcs_blob.name.split("/")[-1]
    latest_build_result_path = (
        f"{_LATEST_SERVER_DEB_GCS_DIR}/{build_result_filename}")
    logging.info("Copying blob %s (%s) -> %s", gcs_blob, gcs_bucket,
                 latest_build_result_path)
    gcs_bucket.copy_blob(
        gcs_blob, gcs_bucket, new_name=latest_build_result_path)


def main(argv):
  del argv  # Unused.

  if not flags.FLAGS.encrypted_service_key:
    raise ValueError("--encrypted_service_key must be provided.")
  if not flags.FLAGS.build_results_dir:
    raise ValueError("--build_results_dir must be provided.")

  temp_dir = tempfile.mkdtemp()
  service_file_path = os.path.join(temp_dir, _DECRYPTED_SERVICE_FILE_NAME)

  try:
    _DecryptGCPServiceFileTo(service_file_path)
    gcs_client = storage.Client.from_service_account_json(service_file_path)
    gcs_bucket = gcs_client.get_bucket(os.environ[_GCS_BUCKET])
    gcs_build_results_dir = _GetGCSBuildResultsDir()
    _UploadBuildResults(gcs_bucket, gcs_build_results_dir)

    # Upload the generated OpenAPI description and the generated documentation.
    if flags.FLAGS.openapi_json_dir:
      gcs_bucket_openapi = (
          gcs_client.get_bucket(os.environ[_GCS_BUCKET_OPENAPI]))
      _UploadOpenApiJson(gcs_bucket_openapi, "openapi_description")
      _UploadDocumentation(gcs_bucket_openapi, "documentation")
  finally:
    shutil.rmtree(temp_dir)

  if os.environ[_GCS_TAG] == _UBUNTU_64BIT_TAG:
    _TriggerAppveyorBuild(_APPVEYOR_WINDOWS_TEMPLATES_SLUG)
  elif os.environ[_GCS_TAG] == _SERVER_DEB_TAG:
    _UpdateLatestServerDebDirectory(gcs_bucket, gcs_build_results_dir)
    _TriggerAppveyorBuild(_APPVEYOR_E2E_TESTS_SLUG)
    _TriggerAppveyorBuild(_APPVEYOR_DOCKER_BUILD_SLUG)


if __name__ == "__main__":
  app.run(main)
