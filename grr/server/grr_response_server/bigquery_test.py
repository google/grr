#!/usr/bin/env python
# Lint as: python3
"""Tests for grr.lib.bigquery."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import io
import os
import time
from unittest import mock

from absl import app
from googleapiclient import errors

from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.util import temp
from grr_response_core.lib.util.compat import json
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
    schema_data = json.ReadFromPath(schema_path)

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
    bq_client = bigquery.BigQueryClient()

    resp = mock.Mock()
    resp.status = 503
    error = mock.Mock()
    error.resp = resp
    job = mock.Mock()
    # Always raise errors.HttpError on job.execute()
    job.configure_mock(
        **{"execute.side_effect": errors.HttpError(resp, b"nocontent")})
    job_id = "hunts_HFFE1D044_Results_1446056474"

    with temp.AutoTempFilePath() as filepath:
      with io.open(filepath, "w", encoding="utf-8") as filedesc:
        filedesc.write("{data}")

      with mock.patch.object(time, "sleep") as mock_sleep:
        with self.assertRaises(bigquery.BigQueryJobUploadError):
          bq_client.RetryUpload(job, job_id, error)

    # Make sure retry sleeps are correct.
    max_calls = config.CONFIG["BigQuery.retry_max_attempts"]
    retry_interval = config.CONFIG["BigQuery.retry_interval"]
    multiplier = config.CONFIG["BigQuery.retry_multiplier"]

    self.assertEqual(job.execute.call_count, max_calls)
    mock_sleep.assert_has_calls([
        mock.call(retry_interval.ToFractional(rdfvalue.SECONDS)),
        mock.call(retry_interval.ToFractional(rdfvalue.SECONDS) * multiplier)
    ])


def main(argv):
  del argv  # Unused.
  test_lib.main()


if __name__ == "__main__":
  app.run(main)
