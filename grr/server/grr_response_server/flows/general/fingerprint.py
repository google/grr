#!/usr/bin/env python
"""Invoke the fingerprint client action on a file."""

from grr.lib import rdfvalue
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import crypto
from grr.lib.rdfvalues import paths
from grr.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import flows_pb2
from grr.server.grr_response_server import aff4
from grr.server.grr_response_server import flow
from grr.server.grr_response_server import server_stubs
from grr.server.grr_response_server.aff4_objects import aff4_grr


class FingerprintFileArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.FingerprintFileArgs
  rdf_deps = [
      paths.PathSpec,
  ]


class FingerprintFileResult(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.FingerprintFileResult
  rdf_deps = [
      crypto.Hash,
      rdfvalue.RDFURN,
  ]


class FingerprintFileMixin(object):
  """Retrieve all fingerprints of a file."""

  fingerprint_file_mixin_client_action = server_stubs.FingerprintFile

  def FingerprintFile(self, pathspec, max_filesize=None, request_data=None):
    """Launch a fingerprint client action."""
    request = rdf_client.FingerprintRequest(pathspec=pathspec)
    if max_filesize is not None:
      request.max_filesize = max_filesize

    # Generic hash.
    request.AddRequest(
        fp_type=rdf_client.FingerprintTuple.Type.FPT_GENERIC,
        hashers=[
            rdf_client.FingerprintTuple.HashType.MD5,
            rdf_client.FingerprintTuple.HashType.SHA1,
            rdf_client.FingerprintTuple.HashType.SHA256
        ])

    # Authenticode hash.
    request.AddRequest(
        fp_type=rdf_client.FingerprintTuple.Type.FPT_PE_COFF,
        hashers=[
            rdf_client.FingerprintTuple.HashType.MD5,
            rdf_client.FingerprintTuple.HashType.SHA1,
            rdf_client.FingerprintTuple.HashType.SHA256
        ])

    self.CallClient(
        self.fingerprint_file_mixin_client_action,
        request,
        next_state="ProcessFingerprint",
        request_data=request_data)

  @flow.StateHandler()
  def ProcessFingerprint(self, responses):
    """Store the fingerprint response."""
    if not responses.success:
      # Its better to raise rather than merely logging since it will make it to
      # the flow's protobuf and users can inspect the reason this flow failed.
      raise flow.FlowError("Could not fingerprint file: %s" % responses.status)

    response = responses.First()
    if response.pathspec.path:
      urn = response.pathspec.AFF4Path(self.client_id)
    else:
      urn = self.args.pathspec.AFF4Path(self.client_id)
    self.state.urn = urn

    with aff4.FACTORY.Create(
        urn, aff4_grr.VFSFile, mode="w", token=self.token) as fd:
      hash_obj = response.hash
      fd.Set(fd.Schema.HASH, hash_obj)

    self.ReceiveFileFingerprint(
        urn, hash_obj, request_data=responses.request_data)

  def ReceiveFileFingerprint(self, urn, hash_obj, request_data=None):
    """This method will be called with the new urn and the received hash."""


class FingerprintFile(FingerprintFileMixin, flow.GRRFlow):
  """Retrieve all fingerprints of a file."""

  category = "/Filesystem/"
  args_type = FingerprintFileArgs
  behaviours = flow.GRRFlow.behaviours + "ADVANCED"

  @flow.StateHandler()
  def Start(self):
    """Issue the fingerprinting request."""
    self.FingerprintFile(self.args.pathspec)

  def ReceiveFileFingerprint(self, urn, hash_obj, request_data=None):
    # Notify any parent flows.
    self.SendReply(FingerprintFileResult(file_urn=urn, hash_entry=hash_obj))

  @flow.StateHandler()
  def End(self):
    """Finalize the flow."""
    super(FingerprintFile, self).End()

    self.Status("Finished fingerprinting %s", self.args.pathspec.path)
