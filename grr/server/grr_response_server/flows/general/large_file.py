#!/usr/bin/env python
"""A module with the implementation of the large file collection flow."""
import os

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


class CollectLargeFileFlow(flow_base.FlowBase):
  """A flow mixing with large file collection logic."""

  friendly_name = "Collect large file"
  category = "/Filesystem/"
  behaviours = flow_base.BEHAVIOUR_BASIC

  args_type = CollectLargeFileFlowArgs

  def Start(self) -> None:
    super().Start()

    # The encryption key is generated and stored within flow state to let the
    # analyst decrypt the file later.
    self.state.encryption_key = os.urandom(16)

    args = rdf_large_file.CollectLargeFileArgs()
    args.path_spec = self.args.path_spec
    args.signed_url = self.args.signed_url
    args.encryption_key = self.state.encryption_key

    self.CallClient(
        server_stubs.CollectLargeFile,
        args,
        next_state=self.Collect.__name__,
        callback_state=self.Callback.__name__)

  def Collect(self, responses: _Responses) -> None:
    # Do nothing, everything is handled by the callback state method.
    pass

  def Callback(self, responses: _Responses) -> None:
    if not responses.success:
      raise flow_base.FlowError(f"Failed to start upload: {responses.status}")

    # TODO: Once progress updates are expected we should be fine
    # with more responses. For now though, only a single response is expected
    # and it should set session URL.
    if "session_url" in self.state:
      raise ValueError("Session URL already received.")
    if len(responses) != 1:
      raise ValueError(f"Unexpected number of responses: {len(responses)}")

    response = responses.First()
    if not isinstance(response, rdf_large_file.CollectLargeFileResult):
      raise TypeError(f"Unexpected response type: {type(response)}")

    self.state.session_uri = response.session_uri
