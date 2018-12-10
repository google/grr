#!/usr/bin/env python
"""Invoke the fingerprint client action on a file."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client_action as rdf_client_action
from grr_response_core.lib.rdfvalues import crypto as rdf_crypto
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import flows_pb2
from grr_response_server import aff4
from grr_response_server import data_store
from grr_response_server import flow
from grr_response_server import flow_base
from grr_response_server import server_stubs
from grr_response_server.aff4_objects import aff4_grr
from grr_response_server.rdfvalues import objects as rdf_objects


class FingerprintFileArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.FingerprintFileArgs
  rdf_deps = [
      rdf_paths.PathSpec,
  ]


class FingerprintFileResult(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.FingerprintFileResult
  rdf_deps = [
      rdf_crypto.Hash,
      rdfvalue.RDFURN,
  ]


class FingerprintFileLogic(object):
  """Retrieve all fingerprints of a file."""

  fingerprint_file_mixin_client_action = server_stubs.FingerprintFile

  def FingerprintFile(self, pathspec, max_filesize=None, request_data=None):
    """Launch a fingerprint client action."""
    request = rdf_client_action.FingerprintRequest(pathspec=pathspec)
    if max_filesize is not None:
      request.max_filesize = max_filesize

    # Generic hash.
    request.AddRequest(
        fp_type=rdf_client_action.FingerprintTuple.Type.FPT_GENERIC,
        hashers=[
            rdf_client_action.FingerprintTuple.HashType.MD5,
            rdf_client_action.FingerprintTuple.HashType.SHA1,
            rdf_client_action.FingerprintTuple.HashType.SHA256
        ])

    # Authenticode hash.
    request.AddRequest(
        fp_type=rdf_client_action.FingerprintTuple.Type.FPT_PE_COFF,
        hashers=[
            rdf_client_action.FingerprintTuple.HashType.MD5,
            rdf_client_action.FingerprintTuple.HashType.SHA1,
            rdf_client_action.FingerprintTuple.HashType.SHA256
        ])

    self.CallClient(
        self.fingerprint_file_mixin_client_action,
        request,
        next_state="ProcessFingerprint",
        request_data=request_data)

  def ProcessFingerprint(self, responses):
    """Store the fingerprint response."""
    if not responses.success:
      # Its better to raise rather than merely logging since it will make it to
      # the flow's protobuf and users can inspect the reason this flow failed.
      raise flow.FlowError("Could not fingerprint file: %s" % responses.status)

    response = responses.First()
    if response.pathspec.path:
      pathspec = response.pathspec
    else:
      pathspec = self.args.pathspec

    self.state.urn = pathspec.AFF4Path(self.client_urn)

    hash_obj = response.hash

    if data_store.AFF4Enabled():
      with aff4.FACTORY.Create(
          self.state.urn, aff4_grr.VFSFile, mode="w", token=self.token) as fd:
        fd.Set(fd.Schema.HASH, hash_obj)

    if data_store.RelationalDBWriteEnabled():
      path_info = rdf_objects.PathInfo.FromPathSpec(pathspec)
      path_info.hash_entry = response.hash

      data_store.REL_DB.WritePathInfos(self.client_id, [path_info])

    self.ReceiveFileFingerprint(
        self.state.urn, hash_obj, request_data=responses.request_data)

  def ReceiveFileFingerprint(self, urn, hash_obj, request_data=None):
    """This method will be called with the new urn and the received hash."""


@flow_base.DualDBFlow
class FingerprintFileMixin(FingerprintFileLogic):
  """Retrieve all fingerprints of a file."""

  category = "/Filesystem/"
  args_type = FingerprintFileArgs
  behaviours = flow.GRRFlow.behaviours + "ADVANCED"

  def Start(self):
    """Issue the fingerprinting request."""
    super(FingerprintFileMixin, self).Start()

    self.FingerprintFile(self.args.pathspec)

  def ReceiveFileFingerprint(self, urn, hash_obj, request_data=None):
    # Notify any parent flows.
    self.SendReply(FingerprintFileResult(file_urn=urn, hash_entry=hash_obj))

  def End(self, responses):
    """Finalize the flow."""
    super(FingerprintFileMixin, self).End(responses)

    self.Log("Finished fingerprinting %s", self.args.pathspec.path)
