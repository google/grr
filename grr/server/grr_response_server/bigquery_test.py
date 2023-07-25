#!/usr/bin/env python
"""Tests for grr.lib.bigquery."""

import io
import json
import os
import time
from unittest import mock

from absl import app
from googleapiclient import errors

from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.util import temp
from grr_response_server import bigquery
from grr.test_lib import test_lib


class BigQueryClientTest(test_lib.GRRBaseTest):
  """Tests BigQuery client."""
  PROJECT_ID = "grr-dummy"
  SERVICE_ACCOUNT_JSON = """{"type": "service_account"}"""

  @mock.patch.object(bigquery, "ServiceAccountCredentials")
  @mock.patch.object(bigquery.discovery, "build")
  @mock.patch.object(bigquery.httplib2, "Http")
  def testInsertData(self, mock_http, mock_build, mock_creds):
    bq_client = bigquery.GetBigQueryClient(
        service_account_json=self.SERVICE_ACCOUNT_JSON,
        project_id=self.PROJECT_ID)

    schema_path = os.path.join(config.CONFIG["Test.data_dir"], "bigquery",
                               "ExportedFile.schema")
    with open(schema_path, mode="rt", encoding="utf-8") as schema_file:
      schema_data = json.load(schema_file)

    data_fd = open(
        os.path.join(config.CONFIG["Test.data_dir"], "bigquery",
                     "ExportedFile.json.gz"), "rb")
    now = rdfvalue.RDFDatetime.Now().AsSecondsSinceEpoch()
    job_id = "hunts_HFFE1D044_Results_%s" % now
    bq_client.InsertData("ExportedFile", data_fd, schema_data, job_id)

    # We should have called insert once
    insert = mock_build.return_value.jobs.return_value.insert
    self.assertEqual(insert.call_count, 1)
    self.assertEqual(
        job_id, insert.call_args_list[0][1]["body"]["jobReference"]["jobId"])

  def testRetryUpload(self):
    service = mock.Mock()

    bq_client = bigquery.BigQueryClient(bq_service=service)

    resp = mock.Mock()
    resp.status = 503
    job = mock.Mock()
    # Always raise errors.HttpError on job.execute()
    job.configure_mock(
        **{"execute.side_effect": errors.HttpError(resp, b"nocontent")})
    job_id = "hunts_HFFE1D044_Results_1446056474"

    jobs = mock.Mock()
    jobs.insert.return_value = job

    service.jobs.return_value = jobs

    with temp.AutoTempFilePath() as filepath:
      with io.open(filepath, "w", encoding="utf-8") as filedesc:
        filedesc.write("{data}")

      with io.open(filepath, "rb") as filedesc:
        with mock.patch.object(time, "sleep") as _:
          with self.assertRaises(bigquery.BigQueryJobUploadError):
            bq_client.InsertData("ExportedFile", filedesc, {}, job_id)

    max_calls = config.CONFIG["BigQuery.retry_max_attempts"]
    self.assertEqual(job.execute.call_count, max_calls)


def main(argv):
  del argv  # Unused.
  test_lib.main()


if __name__ == "__main__":
  app.run(main)
