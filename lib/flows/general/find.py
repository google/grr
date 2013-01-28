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

"""Find files on the client."""
import stat
import time

from grr.lib import aff4
from grr.lib import flow
from grr.lib import type_info
from grr.lib import utils


class FindFiles(flow.GRRFlow):
  """Find files on the client.

    The result from this flow is an AFF4Collection which will be created on the
    output path, containing all aff4 objects on the client which match the
    criteria. Note that these files will not be downloaded by this flow, only
    the metadata of the file in fetched.

    Note: This flow is inefficient for collecting a large number of files.

  Returns to parent flow:
    rdfvalue.StatEntry objects for each found file.
  """

  category = "/Filesystem/"

  flow_typeinfo = type_info.TypeDescriptorSet(
      type_info.FindSpecType(
          description="A find descriptor.",
          name="findspec"
          ),

      type_info.String(
          description="A path relative to the client to put the output.",
          name="output",
          default="analysis/find/{u}-{t}"),

      type_info.Number(
          description="Maximum number of results to get.",
          name="max_results",
          default=500),
      )

  @flow.StateHandler(next_state="IterateFind")
  def Start(self, unused_response):
    """Issue the find request to the client."""
    self.path = self.findspec.pathspec.path
    self.received_count = 0

    if self.output:
      # Create the output collection and get it ready.
      output = self.output.format(t=time.time(), u=self.user)
      self.output = aff4.ROOT_URN.Add(self.client_id).Add(output)
      self.collection = aff4.FACTORY.Create(self.output, "AFF4Collection",
                                            mode="w", token=self.token)

      self.collection.Set(self.collection.Schema.DESCRIPTION("Find {0}".format(
          self.findspec)))

    else:
      self.output = None

    self.urn = aff4.ROOT_URN.Add(self.client_id)

    # Build up the request protobuf.
    # Call the client with it
    self.CallClient("Find", self.findspec, next_state="IterateFind")

  @flow.StateHandler(next_state="IterateFind")
  def IterateFind(self, responses):
    """Iterate in this state until no more results are available."""
    if not responses.success:
      raise IOError(responses.status)

    for response in responses:
      # Create the file in the VFS
      vfs_urn = aff4.AFF4Object.VFSGRRClient.PathspecToURN(
          response.hit.pathspec, self.urn)

      response.hit.aff4path = utils.SmartUnicode(vfs_urn)

      # TODO(user): This ends up being fairly expensive.
      if stat.S_ISDIR(response.hit.st_mode):
        fd = aff4.FACTORY.Create(vfs_urn, "VFSDirectory", token=self.token)
      else:
        fd = aff4.FACTORY.Create(vfs_urn, "VFSFile", token=self.token)

      stat_response = fd.Schema.STAT(response.hit)
      fd.Set(stat_response)

      fd.Set(fd.Schema.PATHSPEC(response.hit.pathspec))
      fd.Close(sync=False)

      if self.output:
        # Add the new objects URN to the collection.
        self.collection.Add(stat=stat_response, urn=vfs_urn)

      # Send the stat to the parent flow.
      self.SendReply(stat_response)

    self.received_count += len(responses)

    # Exit if we hit the max result count we wanted or we're finished.
    if (self.received_count < self.max_results and
        responses.iterator.state != responses.iterator.FINISHED):

      self.findspec.iterator = responses.iterator

      # If we are close to max_results reduce the iterator.
      self.findspec.iterator.number = min(
          self.findspec.iterator.number, self.max_results - self.received_count)

      self.CallClient("Find", self.findspec, next_state="IterateFind")
      self.Log("%d files processed.", self.received_count)

  @flow.StateHandler()
  def End(self):
    """Save the collection and notification if output is enabled."""
    if self.output:
      self.collection.Close()

      self.Notify(
          "ViewObject", self.output, u"Found on {0} completed {1} hits".format(
              len(self.collection), self.path))
