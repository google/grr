#!/usr/bin/env python
# Copyright 2012 Google Inc. All Rights Reserved.
"""Invoke the fingerprint client action on a file."""


from grr.lib import aff4
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import type_info


class FingerprintFile(flow.GRRFlow):
  """Retrieve all fingerprints of a file."""

  category = "/Filesystem/"

  flow_typeinfo = type_info.TypeDescriptorSet(
      type_info.PathspecType(
          description="The file path to fingerprint."),
      )

  @flow.StateHandler(next_state="Done")
  def Start(self):
    """Issue the fingerprinting request."""

    request = rdfvalue.FingerprintRequest(
        pathspec=self.state.pathspec)

    # Generic hash.
    request.AddRequest(
        fp_type=rdfvalue.FingerprintTuple.Type.FPT_GENERIC,
        hashers=[rdfvalue.FingerprintTuple.Hash.MD5,
                 rdfvalue.FingerprintTuple.Hash.SHA1,
                 rdfvalue.FingerprintTuple.Hash.SHA256])

    # Authenticode hash.
    request.AddRequest(
        fp_type=rdfvalue.FingerprintTuple.Type.FPT_PE_COFF,
        hashers=[rdfvalue.FingerprintTuple.Hash.MD5,
                 rdfvalue.FingerprintTuple.Hash.SHA1,
                 rdfvalue.FingerprintTuple.Hash.SHA256])

    self.CallClient("FingerprintFile", request, next_state="Done")

  @flow.StateHandler()
  def Done(self, responses):
    """Store the fingerprint response."""
    if not responses.success:
      # Its better to raise rather than merely logging since it will make it to
      # the flow's protobuf and users can inspect the reason this flow failed.
      raise flow.FlowError("Could not fingerprint file: %s" % responses.status)

    response = responses.First()
    if response.pathspec.path:
      urn = aff4.AFF4Object.VFSGRRClient.PathspecToURN(response.pathspec,
                                                       self.client_id)
    else:
      urn = aff4.AFF4Object.VFSGRRClient.PathspecToURN(self.state.pathspec,
                                                       self.client_id)
    self.state.Register("urn", urn)
    fd = aff4.FACTORY.Create(urn, "VFSFile", mode="w", token=self.token)
    fingerprint = fd.Schema.FINGERPRINT(response)
    fd.Set(fingerprint)
    fd.Close(sync=False)

  @flow.StateHandler()
  def End(self):
    """Finalize the flow."""
    self.Notify("ViewObject", self.state.urn, "Fingerprint retrieved.")
    self.Status("Finished fingerprinting %s", self.state.pathspec.path)
    # Notify any parent flows.
    self.SendReply(self.state.urn)
