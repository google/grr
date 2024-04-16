#!/usr/bin/env python
"""Invoke the fingerprint client action on a file."""

from grr_response_core.lib.rdfvalues import client_action as rdf_client_action
from grr_response_server import data_store
from grr_response_server import flow_base
from grr_response_server import server_stubs
from grr_response_server.rdfvalues import mig_objects
from grr_response_server.rdfvalues import objects as rdf_objects


# TODO: Remove this mixin when FileFinder no longer exists.
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
        next_state=self._ProcessFingerprint.__name__,
        request_data=request_data)

  def _ProcessFingerprint(self, responses):
    """Store the fingerprint response."""
    if not responses.success:
      # Its better to raise rather than merely logging since it will make it to
      # the flow's protobuf and users can inspect the reason this flow failed.
      raise flow_base.FlowError("Could not fingerprint file: %s" %
                                responses.status)

    response = responses.First()
    if response.pathspec.path:
      pathspec = response.pathspec
    else:
      pathspec = self.args.pathspec

    self.state.urn = pathspec.AFF4Path(self.client_urn)

    hash_obj = response.hash

    path_info = rdf_objects.PathInfo.FromPathSpec(pathspec)
    path_info.hash_entry = response.hash

    data_store.REL_DB.WritePathInfos(
        self.client_id, [mig_objects.ToProtoPathInfo(path_info)]
    )

    self.ReceiveFileFingerprint(
        self.state.urn, hash_obj, request_data=responses.request_data)

  def ReceiveFileFingerprint(self, urn, hash_obj, request_data=None):
    """This method will be called with the new urn and the received hash."""
