#!/usr/bin/env python
"""Library for interacting with Google BigQuery service."""
import json
import logging

from googleapiclient import discovery
from googleapiclient import errors
from googleapiclient import http
import httplib2

from grr_response_core import config
from grr_response_core.lib.util import retry


# pylint: disable=g-import-not-at-top
try:
  from oauth2client.service_account import ServiceAccountCredentials
except ImportError:
  # Set this so mock won't complain about stubbing it.
  ServiceAccountCredentials = None
# pylint: enable=g-import-not-at-top

BIGQUERY_SCOPE = "https://www.googleapis.com/auth/bigquery"


class Error(Exception):
  """Base error class."""


class BigQueryJobUploadError(Error):
  """Failed to create BigQuery upload job."""


def GetBigQueryClient(service_account_json=None,
                      project_id=None,
                      dataset_id=None):
  """Create a BigQueryClient."""
  service_account_data = (
      service_account_json or config.CONFIG["BigQuery.service_acct_json"])
  project_id = project_id or config.CONFIG["BigQuery.project_id"]
  dataset_id = dataset_id or config.CONFIG["BigQuery.dataset_id"]

  if not (service_account_data and project_id and dataset_id):
    raise RuntimeError("BigQuery.service_account_json, "
                       "BigQuery.project_id and BigQuery.dataset_id "
                       "must be defined.")

  creds = ServiceAccountCredentials.from_json_keyfile_dict(
      json.loads(service_account_data), scopes=BIGQUERY_SCOPE
  )
  http_obj = httplib2.Http()
  http_obj = creds.authorize(http_obj)
  service = discovery.build("bigquery", "v2", http=http_obj)
  return BigQueryClient(
      project_id=project_id, bq_service=service, dataset_id=dataset_id)


class BigQueryClient(object):
  """Class for interacting with BigQuery."""

  def __init__(self, project_id=None, bq_service=None, dataset_id=None):
    self.tables = {}
    self.datasets = {}
    self.project_id = project_id
    self.service = bq_service
    self.dataset_id = dataset_id

  def GetSchema(self, table_id, project_id, schema):
    return {
        "schema": {
            "fields": schema
        },
        "tableReference": {
            "tableId": table_id,
            "projectId": project_id,
            "datasetId": self.dataset_id
        }
    }

  def CreateDataset(self):
    """Create a dataset."""
    body = {
        "datasetReference": {
            "datasetId": self.dataset_id,
            "description": "Data exported from GRR",
            "friendlyName": "GRRExportData",
            "projectId": self.project_id
        }
    }
    result = self.service.datasets().insert(
        projectId=self.project_id, body=body).execute()
    self.datasets[self.dataset_id] = result
    return result

  def GetDataset(self, dataset_id):
    if dataset_id not in self.datasets:
      try:
        result = self.service.datasets().get(
            projectId=self.project_id, datasetId=dataset_id).execute()
        self.datasets[dataset_id] = result
      except errors.HttpError:
        return None

    return self.datasets[dataset_id]

  def IsErrorRetryable(self, e):
    """Return true if we should retry on this error.

    Default status codes come from this advice:
    https://developers.google.com/api-client-library/python/guide/media_upload

    Args:
      e: errors.HttpError object.
    Returns:
      boolean
    """
    return e.resp.status in config.CONFIG["BigQuery.retry_status_codes"]

  def InsertData(self, table_id, fd, schema, job_id):
    """Insert data into a bigquery table.

    If the table specified doesn't exist, it will be created with the specified
    schema.

    Args:
      table_id: string table id
      fd: open file descriptor containing the newline separated JSON
      schema: BigQuery schema dict
      job_id: string job id

    Returns:
      API response object on success, None on failure
    """
    configuration = {
        "schema": {
            "fields": schema
        },
        "destinationTable": {
            "projectId": self.project_id,
            "tableId": table_id,
            "datasetId": self.dataset_id
        },
        "sourceFormat": "NEWLINE_DELIMITED_JSON",
    }

    body = {
        "configuration": {
            "load": configuration
        },
        "jobReference": {
            "projectId": self.project_id,
            "jobId": job_id
        }
    }

    # File content can be gzipped for bandwidth efficiency. The server handles
    # it correctly without any changes to the request.
    mediafile = http.MediaFileUpload(
        fd.name, mimetype="application/octet-stream")
    job = self.service.jobs().insert(
        projectId=self.project_id, body=body, media_body=mediafile)

    first_try = True

    @retry.When(
        errors.HttpError,
        self.IsErrorRetryable,
        opts=retry.Opts(
            attempts=config.CONFIG["BigQuery.retry_max_attempts"],
            init_delay=config.CONFIG["BigQuery.retry_interval"].AsTimedelta(),
            backoff=config.CONFIG["BigQuery.retry_multiplier"],
        ),
    )
    def Execute() -> None:
      nonlocal first_try

      try:
        job.execute()
      except errors.HttpError:
        if first_try:
          first_try = False

          if self.GetDataset(self.dataset_id):
            logging.exception("Error with job: %s", job_id)
          else:
            # If this is our first export ever, we need to create the dataset.
            logging.info("Attempting to create dataset: %s", self.dataset_id)
            self.CreateDataset()

        raise

    try:
      Execute()
    except errors.HttpError as error:
      raise BigQueryJobUploadError(f"Failed job '{job_id}'") from error
