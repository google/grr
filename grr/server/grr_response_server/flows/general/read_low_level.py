#!/usr/bin/env python
"""Flow that reads data low level."""
import logging

from grr_response_core.lib.rdfvalues import read_low_level as rdf_read_low_level
from grr_response_server import data_store
from grr_response_server import file_store
from grr_response_server import flow_base
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

  def Start(self):
    """Schedules the read in the client (ReadLowLevel ClientAction)."""
    # TODO: Set `blob_size` according to `sector_block_size`.
    request = rdf_read_low_level.ReadLowLevelRequest(
        path=self.args.path, length=self.args.length, offset=self.args.offset)
    if self.args.HasField("sector_block_size"):
      request.sector_block_size = self.args.sector_block_size

    if not self.client_version or self.client_version >= 3459:
      self.CallClient(
          server_stubs.ReadLowLevel,
          request,
          next_state=self.StoreBlobsAsTmpFile.__name__)
    else:
      raise flow_base.FlowError("ReadLowLevel Flow is only supported on "
                                "client version 3459 or higher (target client "
                                f"version is {self.client_version}).")

  def StoreBlobsAsTmpFile(self, responses):
    """Stores bytes retrieved from client in the VFS tmp folder."""
    if not responses.success:
      raise flow_base.FlowError(responses.status)

    file_size = 0
    file_hash_from_client = None  # Hash on the last buffer reference.
    blob_refs = []

    smallest_offset = None
    biggest_offset = 0
    for response in responses:
      file_size += response.blob.length
      if smallest_offset is None or response.blob.offset < smallest_offset:
        smallest_offset = response.blob.offset
      if response.blob.offset >= biggest_offset:
        biggest_offset = response.blob.offset
        file_hash_from_client = response.accumulated_hash

      blob_refs.append(
          rdf_objects.BlobReference(
              offset=response.blob.offset,
              size=response.blob.length,
              blob_id=rdf_objects.BlobID.FromSerializedBytes(
                  response.blob.data)))

    if file_size < self.args.length:
      self.Log(f"Read less bytes than requested ({file_size} < "
               f"{self.args.length}). The file is probably smaller than "
               "requested read length.")
    elif file_size > self.args.length:
      raise flow_base.FlowError(f"Read more bytes than requested ({file_size} >"
                                f" {self.args.length}).")

    # This raw data is not necessarily a file, but any data from the device.
    # We artificially create a filename to refer to it on our file store.
    alphanumeric_only = "".join(c for c in self.args.path if c.isalnum())
    # TODO: Remove client_id from `tmp_filename` when bug is fixed.
    tmp_filename = f"{self.client_id}_{self.rdf_flow.flow_id}_{alphanumeric_only}"
    tmp_filepath = db.ClientPath.Temp(self.client_id, [tmp_filename])

    # Store blobs under this name in file_store.
    file_hash_from_store = file_store.AddFileWithUnknownHash(
        tmp_filepath, blob_refs, use_external_stores=False)

    # Check if the file hashes match, and log in case they don't.
    file_hash_id_from_client = rdf_objects.SHA256HashID.FromSerializedBytes(
        file_hash_from_client.AsBytes())
    if file_hash_id_from_client != file_hash_from_store:
      logging.warning(
          "Flow %s (%s): mismatch in file hash id in the storage (%s) and in the client (%s)",
          self.rdf_flow.protobuf.flow_id, self.client_id, file_hash_from_store,
          file_hash_from_client)

    path_info = rdf_objects.PathInfo.Temp(components=[tmp_filename])
    path_info.hash_entry.sha256 = file_hash_from_store.AsBytes()
    path_info.hash_entry.num_bytes = file_size
    path_info.hash_entry.source_offset = smallest_offset

    # Store file reference for this client in data_store.
    data_store.REL_DB.WritePathInfos(self.client_id, [path_info])

    result = rdf_read_low_level.ReadLowLevelFlowResult(path=tmp_filename)
    self.SendReply(result)

  def Done(self, responses):
    if not responses.success:
      raise flow_base.FlowError(responses.status.error_message)
