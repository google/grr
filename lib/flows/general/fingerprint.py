#!/usr/bin/env python
# Copyright 2012 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
        pathspec=self.pathspec)

    # Generic hash.
    request.AddRequest(
        fp_type=rdfvalue.FingerprintTuple.Enum("FPT_GENERIC"),
        hashers=[rdfvalue.FingerprintTuple.Enum("MD5"),
                 rdfvalue.FingerprintTuple.Enum("SHA1"),
                 rdfvalue.FingerprintTuple.Enum("SHA256")])

    # Authenticode hash.
    request.AddRequest(
        fp_type=rdfvalue.FingerprintTuple.Enum("FPT_PE_COFF"),
        hashers=[rdfvalue.FingerprintTuple.Enum("MD5"),
                 rdfvalue.FingerprintTuple.Enum("SHA1"),
                 rdfvalue.FingerprintTuple.Enum("SHA256")])

    self.CallClient("FingerprintFile", request, next_state="Done")

  @flow.StateHandler()
  def Done(self, responses):
    """Store the fingerprint response."""
    if not responses.success:
      # Its better to raise rather than merely logging since it will make it to
      # the flow's protobuf and users can inspect the reason this flow failed.
      raise flow.FlowError("Could not fingerprint file: %s" % responses.status)

    response = responses.First()

    # TODO(user): This is a bug - the fingerprinter client action should
    # return the pathspec it actually created to access the file - this corrects
    # for file casing etc.
    self.urn = aff4.AFF4Object.VFSGRRClient.PathspecToURN(self.pathspec,
                                                          self.client_id)
    fd = aff4.FACTORY.Create(self.urn, "VFSFile", mode="w", token=self.token)
    fingerprint = fd.Schema.FINGERPRINT(response)
    fd.Set(fingerprint)
    fd.Close(sync=False)

  @flow.StateHandler()
  def End(self):
    """Finalize the flow."""
    self.Notify("ViewObject", self.urn, "Fingerprint retrieved.")
    self.Status("Finished fingerprinting %s", self.pathspec.path)
    # Notify any parent flows.
    self.SendReply(self.urn)
