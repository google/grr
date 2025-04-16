#!/usr/bin/env python
"""GCS output plugin for FileFinder flow results."""

import jinja2
import json
import logging

from typing import Any, Dict

from google.cloud import storage
from google.protobuf import json_format
from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import standard as rdf_standard
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import output_plugin_pb2
from grr_response_server import data_store
from grr_response_server import file_store
from grr_response_server import output_plugin
from grr_response_server.databases import db

JsonDict = Dict[str, Any]

class GcsOutputPluginArgs(rdf_structs.RDFProtoStruct):
  protobuf = output_plugin_pb2.GcsOutputPluginArgs


class GcsOutputPlugin(output_plugin.OutputPlugin):
  """An output plugin that sends the object to GCS for each response received."""
  name = "GCS Bucket"
  description = "Send to GCS for each result."
  args_type = GcsOutputPluginArgs
  produces_output_streams = False
  uploaded_files = 0


  def UploadBlobFromStream(self, project_id, bucket_name, client_path, client_id, flow_id, destination_blob_name):
    """Uploads bytes from a stream to a blob"""
    storage_client = storage.Client(project=project_id)
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(client_id+"/"+flow_id+destination_blob_name)
    fd = file_store.OpenFile(client_path)
    fd.seek(0)
    blob.upload_from_file(fd)

  def ProcessResponse(self, state, response):
    """Sends objects to GCS for each response."""

    client_id = response.client_id
    flow_id = response.flow_id

    if response.HasField("payload"):
        if response.payload.HasField("transferred_file"):
            if response.payload.stat_entry.st_size > 0 :
                client_path = db.ClientPath.FromPathSpec(client_id, response.payload.stat_entry.pathspec)
                self.UploadBlobFromStream(self.args.project_id, self.args.gcs_bucket, client_path, client_id, flow_id, response.payload.stat_entry.pathspec.path)
                logging.info("response client_id: %s, flow_id: %s, transferred_file: %s", client_id, flow_id, response.payload.stat_entry.pathspec.path)
                self.uploaded_files += 1
            else:
                logging.warning("%s : file size is 0, nothing to push to GCS", response.payload.stat_entry.pathspec.path)


  def ProcessResponses(self, state, responses):
    if self.args.gcs_bucket == "" or self.args.project_id == "":
        logging.error("both GCS bucket and Project ID must be set")
        return
    else:
        logging.info("Project ID: %s, GCS bucket: %s", self.args.project_id, self.args.gcs_bucket)

    for response in responses:
      self.ProcessResponse(state, response)