#!/usr/bin/env python
"""Library for interacting with Google BigQuery service."""


import logging
import time


from apiclient.discovery import build
from apiclient.errors import HttpError
from apiclient.http import MediaFileUpload
import httplib2
from oauth2client.client import SignedJwtAssertionCredentials

from grr.lib import config_lib

BIGQUERY_SCOPE = "https://www.googleapis.com/auth/bigquery"


class Error(Exception):
  """Base error class."""


class BigQueryJobUploadError(Error):
  """Failed to create BigQuery uplod job."""


def GetBigQueryClient(service_account=None,
                      private_key=None,
                      project_id=None,
                      dataset_id=None):
  """Create a BigQueryClient."""
  service_account = service_account or config_lib.CONFIG[
      "BigQuery.service_account"]
  private_key = private_key or config_lib.CONFIG["BigQuery.private_key"]
  project_id = project_id or config_lib.CONFIG["BigQuery.project_id"]
  dataset_id = dataset_id or config_lib.CONFIG["BigQuery.dataset_id"]

  if not (service_account and private_key and project_id and dataset_id):
    raise RuntimeError("BigQuery.service_account, BigQuery.private_key, "
                       "BigQuery.project_id and BigQuery.dataset_id "
                       "must be defined.")

  creds = SignedJwtAssertionCredentials(service_account,
                                        private_key,
                                        scope=BIGQUERY_SCOPE)
  http = httplib2.Http()
  http = creds.authorize(http)
  service = build("bigquery", "v2", http=http)
  return BigQueryClient(project_id=project_id,
                        bq_service=service,
                        dataset_id=dataset_id)


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
        "schema": {"fields": schema},
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
    result = self.service.datasets().insert(projectId=self.project_id,
                                            body=body).execute()
    self.datasets[self.dataset_id] = result
    return result

  def GetDataset(self, dataset_id):
    if dataset_id not in self.datasets:
      try:
        result = self.service.datasets().get(projectId=self.project_id,
                                             datasetId=dataset_id).execute()
        self.datasets[dataset_id] = result
      except HttpError:
        return None

    return self.datasets[dataset_id]

  def IsErrorRetryable(self, e):
    """Return true if we should retry on this error.

    Default status codes come from this advice:
    https://developers.google.com/api-client-library/python/guide/media_upload

    Args:
      e: HttpError object.
    Returns:
      boolean
    """
    return e.resp.status in config_lib.CONFIG["BigQuery.retry_status_codes"]

  def RetryUpload(self, job, job_id, error):
    """Retry the BigQuery upload job.

    Using the same job id protects us from duplicating data on the server. If we
    fail all of our retries we raise.

    Args:
      job: BigQuery job object
      job_id: ID string for this upload job
      error: HttpError object from the first error

    Returns:
      API response object on success, None on failure
    Raises:
      BigQueryJobUploadError: if we can't get the bigquery job started after
          retry_max_attempts
    """
    if self.IsErrorRetryable(error):
      retry_count = 0
      sleep_interval = config_lib.CONFIG["BigQuery.retry_interval"]
      while retry_count < config_lib.CONFIG["BigQuery.retry_max_attempts"]:

        time.sleep(sleep_interval.seconds)
        logging.info("Retrying job_id: %s", job_id)
        retry_count += 1

        try:
          response = job.execute()
          return response
        except HttpError as e:
          if self.IsErrorRetryable(e):
            sleep_interval *= config_lib.CONFIG["BigQuery.retry_multiplier"]
            logging.exception("Error with job: %s, will retry in %s", job_id,
                              sleep_interval)
          else:
            raise BigQueryJobUploadError("Can't retry error code %s. Giving up"
                                         " on job: %s.", e.resp.status, job_id)
    else:
      raise BigQueryJobUploadError("Can't retry error code %s. Giving up on "
                                   "job: %s.", error.resp.status, job_id)

    raise BigQueryJobUploadError("Giving up on job:%s after %s retries.",
                                 job_id, retry_count)

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
        "schema": {"fields": schema},
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
    mediafile = MediaFileUpload(fd.name, mimetype="application/octet-stream")
    job = self.service.jobs().insert(projectId=self.project_id,
                                     body=body,
                                     media_body=mediafile)
    try:
      response = job.execute()
      return response
    except HttpError as e:
      if self.GetDataset(self.dataset_id):
        logging.exception("Error with job: %s", job_id)
      else:
        # If this is our first export ever, we need to create the dataset.
        logging.info("Attempting to create dataset: %s", self.dataset_id)
        self.CreateDataset()
      return self.RetryUpload(job, job_id, e)
