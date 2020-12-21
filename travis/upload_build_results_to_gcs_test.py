#!/usr/bin/env python
# python3
import os
import subprocess
from unittest import mock

from absl.testing import absltest
import requests

from grr.travis import upload_build_results_to_gcs


class FakeError(Exception):
  """Fake exception for testing purposes."""


@mock.patch.dict(
    os.environ, {
        upload_build_results_to_gcs._APPVEYOR_TOKEN:
            "fake-appveyor-token",
        upload_build_results_to_gcs._APPVEYOR_ACCOUNT_NAME:
            "fake-account",
        upload_build_results_to_gcs._APPVEYOR_E2E_TESTS_SLUG:
            "fake-slug",
        upload_build_results_to_gcs._APPVEYOR_API_URL:
            "http://fake-site.com/api",
        upload_build_results_to_gcs._TRAVIS_COMMIT:
            "fake-commit",
        upload_build_results_to_gcs._TRAVIS_BRANCH:
            "fake-branch",
        upload_build_results_to_gcs._SERVICE_FILE_ENCRYPTION_KEY_VAR:
            "keyvar",
        upload_build_results_to_gcs._SERVICE_FILE_ENCRYPTION_IV_VAR:
            "ivvar",
        "keyvar":
            "fake-encryption-key",
        "ivvar":
            "fake-encryption-iv",
    })
class GCSUploadTest(absltest.TestCase):

  @mock.patch.object(subprocess, "check_call")
  def testRedactSecretsFromExceptions_Decrypt(self, mock_subprocess):
    mock_subprocess.side_effect = FakeError(
        "Something unexpected happened. "
        "Args: [fake-encryption-key, fake-encryption-iv].")
    with self.assertRaises(
        upload_build_results_to_gcs.DecryptionError) as context:
      upload_build_results_to_gcs._DecryptGCPServiceFileTo("/foo/bar/baz")
    expected_message = (
        "FakeError encountered when trying to decrypt the GCP service key: "
        "Something unexpected happened. Args: [{0}, {0}].".format(
            upload_build_results_to_gcs._REDACTED_SECRET_PLACEHOLDER))
    self.assertEqual(str(context.exception), expected_message)

  @mock.patch.object(requests, "post")
  def testRedactSecretsFromExceptions_Appveyor(self, mock_post):
    mock_post.side_effect = FakeError(
        "Invalid request ['Authorization': 'Bearer fake-appveyor-token']. "
        "Invalid header 'fake-appveyor-token'.")
    with self.assertRaises(
        upload_build_results_to_gcs.AppveyorError) as context:
      upload_build_results_to_gcs._TriggerAppveyorBuild(
          upload_build_results_to_gcs._APPVEYOR_E2E_TESTS_SLUG)
    expected_message = (
        "FakeError encountered on POST request: Invalid request "
        "['Authorization': 'Bearer {0}']. Invalid header '{0}'.").format(
            upload_build_results_to_gcs._REDACTED_SECRET_PLACEHOLDER)
    self.assertEqual(str(context.exception), expected_message)


if __name__ == "__main__":
  absltest.main()
