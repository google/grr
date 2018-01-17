#!/usr/bin/env python
"""Invoke the fingerprint client action on a file."""

from grr.lib import rdfvalue
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import crypto
from grr.lib.rdfvalues import paths
from grr.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import flows_pb2
from grr.server import aff4
from grr.server import flow
from grr.server import server_stubs
from grr.server.aff4_objects import aff4_grr


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

      if response.HasField("hash"):
        hash_obj = response.hash

      else:
        # TODO(user): Deprecate when all clients can send new format
        # responses.
        hash_obj = fd.Schema.HASH()

        for result in response.results:
          if result["name"] == "generic":
            for hash_type in ["md5", "sha1", "sha256"]:
              value = result.GetItem(hash_type)
              if value:
                setattr(hash_obj, hash_type, value)

          if result["name"] == "pecoff":
            for hash_type in ["md5", "sha1", "sha256"]:
              value = result.GetItem(hash_type)
              if value:
                setattr(hash_obj, "pecoff_" + hash_type, value)

            signed_data = result.GetItem("SignedData", [])
            for data in signed_data:
              hash_obj.signed_data.Append(
                  revision=data[0], cert_type=data[1], certificate=data[2])

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

  def NotifyAboutEnd(self):
    try:
      urn = self.state.urn
    except AttributeError:
      self.Notify("FlowStatus", self.client_id,
                  "Unable to fingerprint %s." % self.args.pathspec.path)
      return
    self.Notify("ViewObject", urn, "Fingerprint retrieved.")

  @flow.StateHandler()
  def End(self):
    """Finalize the flow."""
    super(FingerprintFile, self).End()

    self.Status("Finished fingerprinting %s", self.args.pathspec.path)
