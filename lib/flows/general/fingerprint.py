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
from grr.lib import type_info
from grr.proto import jobs_pb2


class FingerprintFile(flow.GRRFlow):
  """Retrieve all fingerprints of a file."""

  category = "/Filesystem/"
  flow_typeinfo = {"pathtype": type_info.ProtoEnum(jobs_pb2.Path, "PathType"),
                   "pathspec": type_info.Proto(jobs_pb2.Path)}

  def __init__(self, path="/",
               pathtype=jobs_pb2.Path.OS,
               device=None, pathspec=None, **kwargs):
    """Constructor.

    Allows declaration of a path or pathspec to compute the fingerprint on.

    Args:
      path: The file path to fingerprint.
      pathtype: Identifies requested path type. Enum from Path protobuf.
      device: Optional raw device that should be accessed.
      pathspec: Use a pathspec instead of a path.
    """
    if pathspec:
      self.pathspec = pathspec
    else:
      self.pathspec = jobs_pb2.Path(path=path, pathtype=int(pathtype))
      if device:
        self.pathspec.device = device
    self.request = jobs_pb2.FingerprintRequest(pathspec=self.pathspec)
    flow.GRRFlow.__init__(self, **kwargs)

  @flow.StateHandler(next_state="Done")
  def Start(self):
    self.CallClient("FingerprintFile", self.request, next_state="Done")

  @flow.StateHandler()
  def Done(self, responses):
    """Store the fingerprint response."""
    if not responses.success:
      # Its better to raise rather than merely logging since it will make it to
      # the flow's protobuf and users can inspect the reason this flow failed.
      raise flow.FlowError("Could not fingerprint file: %s" % responses.status)

    response = responses.First()
    self.urn = aff4.AFF4Object.VFSGRRClient.PathspecToURN(self.pathspec,
                                                          self.client_id)
    fd = aff4.FACTORY.Create(self.urn, "VFSFile", mode="w", token=self.token)
    fingerprint = fd.Schema.FINGERPRINT(response)
    fd.Set(fingerprint)
    fd.Close(sync=False)

  def End(self):
    """Finalize the flow."""
    self.Notify("ViewObject", self.urn, "Fingerprint retrieved.")
    self.Status("Finished fingerprinting %s", self.pathspec.path)
    # Notify any parent flows.
    self.SendReply(self.pathspec)
