#!/usr/bin/env python
"""A module with the implementation of the large file collection flow."""

import datetime
import os

import google.auth
from google.auth import compute_engine
from google.auth.transport import requests
from google.cloud import storage

from grr_response_core import config
from grr_response_core.lib.rdfvalues import large_file as rdf_large_file
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import large_file_pb2
from grr_response_server import flow_base
from grr_response_server import flow_responses
from grr_response_server import server_stubs

_Responses = flow_responses.Responses[rdf_large_file.CollectLargeFileResult]


class CollectLargeFileFlowArgs(rdf_structs.RDFProtoStruct):
  """An RDF wrapper for arguments of the large file collection flow."""

  protobuf = large_file_pb2.CollectLargeFileFlowArgs
  rdf_deps = [
      rdf_paths.PathSpec,
  ]


class CollectLargeFileFlowResult(rdf_structs.RDFProtoStruct):
  """An RDF wrapper for the result of the large file collection flow."""

  protobuf = large_file_pb2.CollectLargeFileFlowResult
  rdf_deps = []


class CollectLargeFileFlowProgress(rdf_structs.RDFProtoStruct):
  """An RDF wrapper for the progress of the large file collection flow."""

  protobuf = large_file_pb2.CollectLargeFileFlowProgress
  rdf_deps = []


class CollectLargeFileFlow(flow_base.FlowBase):
  """A flow mixing with large file collection logic."""

  friendly_name = "Collect large file"
  category = "/Filesystem/"
  block_hunt_creation = True
  behaviours = flow_base.BEHAVIOUR_BASIC

  args_type = CollectLargeFileFlowArgs
  result_types = (CollectLargeFileFlowResult,)
  progress_type = CollectLargeFileFlowProgress

  def GetProgress(self) -> CollectLargeFileFlowProgress:
    if hasattr(self.state, "progress"):
      return self.state.progress
    return CollectLargeFileFlowProgress()

  def Start(self) -> None:
    super().Start()

    self.state.progress = CollectLargeFileFlowProgress(
        session_uri=None,
    )

    # The encryption key is generated and stored within flow state to let the
    # analyst decrypt the file later.
    self.state.encryption_key = os.urandom(16)

    sa_email = config.CONFIG["Server.signed_url_service_account_email"]
    bucket_name = config.CONFIG["Server.signed_url_gcs_bucket_name"]
    expires_hours = config.CONFIG["Server.signed_url_expire_hours"]

    args = rdf_large_file.CollectLargeFileArgs()
    args.path_spec = self.args.path_spec
    args.signed_url = self.args.signed_url
    args.encryption_key = self.state.encryption_key

    if not args.signed_url:
      if not sa_email:
        # Log that no Service Account Email config has been provided
        self.Log(
            "To autocreate a signed URL you need to provide a Service Account"
            " Email:"
            " https://cloud.google.com/storage/docs/access-control/signed-urls#signing-resumable"
        )
      elif not bucket_name:
        # Log that no GCS config has been provided
        self.Log(
            "To autocreate a signed URL you need to provide a GCS Bucket:"
            " https://cloud.google.com/storage/docs/access-control/signed-urls#signing-resumable"
        )
      else:
        head_tail = os.path.split(args.path_spec.path)
        blob_name = (
            self.rdf_flow.client_id
            + "-"
            + self.rdf_flow.flow_id
            + "-"
            + head_tail[1]
        )
        self.Log("Signed URL Service Account email: %s", sa_email)
        self.Log("Signed URL GCS Bucket Name: %s", bucket_name)
        self.Log("Signed URL expires in %s hours", expires_hours)
        self.Log("GCS blob_name: %s", blob_name)
        args.signed_url = self._GenerateResumableUploadURL(
            bucket_name, blob_name, sa_email, expires_hours
        )
        self.Log("Signed URL: %s", args.signed_url)

    self.CallClient(
        server_stubs.CollectLargeFile,
        args,
        next_state=self.Collect.__name__,
        callback_state=self.Callback.__name__,
    )

  def Collect(self, responses: _Responses) -> None:
    if not responses.success:
      raise flow_base.FlowError(responses.status)

    last_response = responses.Last()
    result = CollectLargeFileFlowResult(
        session_uri=last_response.session_uri if last_response else None,
        total_bytes_sent=last_response.total_bytes_sent
        if last_response
        else None,
    )
    self.SendReply(result)

  def Callback(self, responses: _Responses) -> None:
    if not responses.success:
      raise flow_base.FlowError(f"Failed to start upload: {responses.status}")

    # Old clients return 1 response, new clients return 2.
    if not responses or len(responses) > 2:
      raise ValueError(f"Unexpected number of responses: {len(responses)}")

    response = responses.Last()
    if not isinstance(response, rdf_large_file.CollectLargeFileResult):
      raise TypeError(f"Unexpected response type: {type(response)}")

    self.state.session_uri = response.session_uri
    self.state.progress.session_uri = response.session_uri

  def _GenerateResumableUploadURL(
      self, bucket_name: str, blob_name: str, sa_email: str, expires_hours: int
  ) -> str:
    """Generates a v4 signed URL for uploading a blob using HTTP POST."""

    auth_request = requests.Request()
    credentials, project = google.auth.default()
    storage_client = storage.Client(project, credentials)
    bucket = storage_client.lookup_bucket(bucket_name)
    blob = bucket.blob(blob_name)
    expires_at = datetime.datetime.now() + datetime.timedelta(
        hours=expires_hours
    )
    signing_credentials = compute_engine.IDTokenCredentials(
        auth_request, "", service_account_email=sa_email
    )

    signed_url = blob.generate_signed_url(
        version="v4",
        expiration=expires_at,
        method="POST",
        content_type="application/octet-stream",
        headers={
            "X-Goog-Resumable": "start",
            "Content-Type": "application/octet-stream",
        },
        credentials=signing_credentials,
    )

    return signed_url
