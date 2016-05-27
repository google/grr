#!/usr/bin/env python
"""Tests for grr.lib.bigquery."""


import json
import os
import tempfile
import time


from apiclient.errors import HttpError
import mock

from grr.lib import bigquery
from grr.lib import config_lib
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import test_lib


class BigQueryClientTest(test_lib.GRRBaseTest):
  """Tests BigQuery client."""
  TEST_KEY = """-----BEGIN PRIVATE KEY-----\n==\n-----END PRIVATE KEY-----\n"""
  PROJECT_ID = "grr-dummy"
  SERVICE_ACCOUNT = "account@grr-dummy.iam.gserviceaccount.com"

  @mock.patch.object(bigquery, "SignedJwtAssertionCredentials")
  @mock.patch.object(bigquery, "build")
  @mock.patch.object(bigquery.httplib2, "Http")
  def testInsertData(self, mock_http, mock_build, mock_creds):
    bq_client = bigquery.GetBigQueryClient(service_account=self.SERVICE_ACCOUNT,
                                           private_key=self.TEST_KEY,
                                           project_id=self.PROJECT_ID)

    schema_data = json.load(open(os.path.join(config_lib.CONFIG[
        "Test.data_dir"], "bigquery", "ExportedFile.schema")))
    data_fd = open(os.path.join(config_lib.CONFIG[
        "Test.data_dir"], "bigquery", "ExportedFile.json.gz"))
    now = rdfvalue.RDFDatetime().Now().AsSecondsFromEpoch()
    job_id = "hunts_HFFE1D044_Results_%s" % now
    bq_client.InsertData("ExportedFile", data_fd, schema_data, job_id)

    # We should have called insert once
    insert = mock_build.return_value.jobs.return_value.insert
    self.assertEqual(insert.call_count, 1)
    self.assertEqual(job_id, insert.call_args_list[0][1][
        "body"]["jobReference"]["jobId"])

  def testRetryUpload(self):
    bq_client = bigquery.BigQueryClient()

    resp = mock.Mock()
    resp.status = 503
    error = mock.Mock()
    error.resp = resp
    job = mock.Mock()
    # Always raise HttpError on job.execute()
    job.configure_mock(**{"execute.side_effect": HttpError(resp, "nocontent")})
    job_id = "hunts_HFFE1D044_Results_1446056474"

    with tempfile.NamedTemporaryFile() as fd:
      fd.write("{data}")
      with mock.patch.object(time, "sleep") as mock_sleep:
        with self.assertRaises(bigquery.BigQueryJobUploadError):
          bq_client.RetryUpload(job, job_id, error)

    # Make sure retry sleeps are correct.
    max_calls = config_lib.CONFIG["BigQuery.retry_max_attempts"]
    retry_interval = config_lib.CONFIG["BigQuery.retry_interval"]
    multiplier = config_lib.CONFIG["BigQuery.retry_multiplier"]

    self.assertEqual(job.execute.call_count, max_calls)
    mock_sleep.assert_has_calls([mock.call(retry_interval), mock.call(
        retry_interval * multiplier)])


def main(argv):
  test_lib.GrrTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)
