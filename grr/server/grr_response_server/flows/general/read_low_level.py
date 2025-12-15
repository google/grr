#!/usr/bin/env python
"""Flow that reads data low level."""

import logging

from google.protobuf import any_pb2
from grr_response_core.lib.rdfvalues import read_low_level as rdf_read_low_level
from grr_response_proto import jobs_pb2
from grr_response_proto import objects_pb2
from grr_response_proto import read_low_level_pb2
from grr_response_server import data_store
from grr_response_server import file_store
from grr_response_server import flow_base
from grr_response_server import flow_responses
from grr_response_server import server_stubs
from grr_response_server.databases import db
from grr_response_server.rdfvalues import objects as rdf_objects


# TODO: Consider allowing big files using external store.
class ReadLowLevel(flow_base.FlowBase):
  """A low-level transfer mechanism for raw data from a device.

  This flow reads and collects `length` bytes from a given `path` starting at
  the provided `offset`.

  Returns to parent flow:
    A ReadLowLevelResult with information on the temporary file created with the
    raw data.
  """

  category = "/Filesystem/"
  args_type = rdf_read_low_level.ReadLowLevelArgs
  result_types = (rdf_read_low_level.ReadLowLevelFlowResult,)

  proto_args_type = read_low_level_pb2.ReadLowLevelArgs
  proto_result_types = (read_low_level_pb2.ReadLowLevelFlowResult,)
  only_protos_allowed = True

  def Start(self):
    """Schedules the read in the client (ReadLowLevel ClientAction)."""
    # TODO: Set `blob_size` according to `sector_block_size`.
    request = read_low_level_pb2.ReadLowLevelRequest(
        path=self.proto_args.path,
        length=self.proto_args.length,
        offset=self.proto_args.offset,
    )
    if self.proto_args.HasField("sector_block_size"):
      request.sector_block_size = self.proto_args.sector_block_size

    if not self.client_version or self.client_version >= 3459:
      self.CallClientProto(
          server_stubs.ReadLowLevel,
          request,
          next_state=self.StoreBlobsAsTmpFile.__name__,
      )
    else:
      raise flow_base.FlowError(
          "ReadLowLevel Flow is only supported on "
          "client version 3459 or higher (target client "
          f"version is {self.client_version})."
      )

  @flow_base.UseProto2AnyResponses
  def StoreBlobsAsTmpFile(
      self, responses: flow_responses.Responses[any_pb2.Any]
  ) -> None:
    """Stores bytes retrieved from client in the VFS tmp folder."""
    if not responses.success:
      raise flow_base.FlowError(responses.status)

    file_size = 0
    file_hash_from_client = None  # Hash on the last buffer reference.
    rdf_blob_refs = []

    smallest_offset = None
    biggest_offset = 0
    for response_any in responses:
      response = read_low_level_pb2.ReadLowLevelResult()
      response.ParseFromString(response_any.value)

      file_size += response.blob.length
      if smallest_offset is None or response.blob.offset < smallest_offset:
        smallest_offset = response.blob.offset
      if response.blob.offset >= biggest_offset:
        biggest_offset = response.blob.offset
        file_hash_from_client = response.accumulated_hash

      rdf_blob_refs.append(
          rdf_objects.BlobReference(
              offset=response.blob.offset,
              size=response.blob.length,
              blob_id=response.blob.data,
          )
      )

    if file_size < self.proto_args.length:
      self.Log(
          f"Read less bytes than requested ({file_size} < "
          f"{self.proto_args.length}). The file is probably smaller than "
          "requested read length."
      )
    elif file_size > self.proto_args.length:
      raise flow_base.FlowError(
          f"Read more bytes than requested ({file_size} >"
          f" {self.proto_args.length})."
      )

    # This raw data is not necessarily a file, but any data from the device.
    # We artificially create a filename to refer to it on our file store.
    alphanumeric_only = "".join(c for c in self.proto_args.path if c.isalnum())
    # TODO: Remove client_id from `tmp_filename` when bug is fixed.
    tmp_filename = (
        f"{self.client_id}_{self.rdf_flow.flow_id}_{alphanumeric_only}"
    )
    tmp_filepath = db.ClientPath.Temp(self.client_id, [tmp_filename])

    # Store blobs under this name in file_store.
    file_hash_from_store = file_store.AddFileWithUnknownHash(
        tmp_filepath, rdf_blob_refs, use_external_stores=False
    )

    # Check if the file hashes match, and log in case they don't.
    file_hash_id_from_client = rdf_objects.SHA256HashID.FromSerializedBytes(
        file_hash_from_client
    )
    if file_hash_id_from_client != file_hash_from_store:
      logging.warning(
          "Flow %s (%s): mismatch in file hash id in the storage (%s) and in"
          " the client (%s)",
          self.rdf_flow.protobuf.flow_id,
          self.client_id,
          file_hash_from_store,
          file_hash_from_client,
      )

    path_info = objects_pb2.PathInfo(
        path_type=objects_pb2.PathInfo.PathType.TEMP,
        components=[tmp_filename],
        hash_entry=jobs_pb2.Hash(
            sha256=file_hash_from_store.AsBytes(),
            num_bytes=file_size,
            source_offset=smallest_offset,
        ),
    )
    # Store file reference for this client in data_store.
    data_store.REL_DB.WritePathInfos(self.client_id, [path_info])

    result = read_low_level_pb2.ReadLowLevelFlowResult(path=tmp_filename)
    self.SendReplyProto(result)

  @flow_base.UseProto2AnyResponses
  def Done(self, responses: flow_responses.Responses[any_pb2.Any]) -> None:
    if not responses.success:
      raise flow_base.FlowError(
          responses.status.error_message
          if responses.status
          else responses.status
      )
