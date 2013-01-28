#!/usr/bin/env python
# Copyright 2011 Google Inc.
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


"""Flows that often get reused by other flows."""



import logging
import stat

from grr.lib import aff4
from grr.lib import flow
from grr.lib import type_info


class DownloadDirectory(flow.GRRFlow):
  """Flow for recursively downloading all files in a directory."""

  category = "/Filesystem/"

  flow_typeinfo = type_info.TypeDescriptorSet(
      type_info.PathspecType(
          description="The pathspec for the directory to list."),
      type_info.Number(
          name="depth",
          description="Maximum recursion depth.",
          default=10),
      type_info.Bool(
          name="ignore_errors",
          description=("If True, we do not raise an error in the case"
                       "that a directory or file cannot be not found."),
          default=False)
      )

  @flow.StateHandler(next_state="DownloadDir")
  def Start(self, unused_response):
    """Issue a request to list the directory."""
    self.urn = aff4.ROOT_URN.Add(self.client_id)
    self.out_urn = None
    self.CallClient("ListDirectory", pathspec=self.pathspec,
                    next_state="DownloadDir",
                    request_data=dict(depth=self.depth))

  @flow.StateHandler(next_state=["DownloadDir", "Done"])
  def DownloadDir(self, responses):
    """Download all files in a given directory recursively."""

    if not responses.success:
      if not self.ignore_errors:
        err = "Error downloading directory: %s" % responses.status
        logging.error(err)
        raise flow.FlowError(err)
    else:
      depth = responses.request_data["depth"] - 1

      for stat_response in responses:
        # Retrieve where the files are being stored in the VFS.
        if not self.out_urn:
          self.out_urn = aff4.AFF4Object.VFSGRRClient.PathspecToURN(
              stat_response.pathspec, self.client_id).Dirname()

        if stat.S_ISDIR(stat_response.st_mode):
          # No need to traverse subdirectories if the current depth is 0
          if depth > 0:
            self.CallClient("ListDirectory", next_state="DownloadDir",
                            pathspec=stat_response.pathspec,
                            request_data=dict(depth=depth))
        else:
          if stat.S_ISREG(stat_response.st_mode):
            self.CallFlow("GetFile", pathspec=stat_response.pathspec,
                          next_state="Done")

  @flow.StateHandler()
  def Done(self, responses):
    if not responses.success:
      if not self.ignore_errors:
        err = "Error downloading file %s" % responses.status
        logging.error(err)
        raise flow.FlowError(err)

  @flow.StateHandler()
  def End(self):
    if self.out_urn:
      self.Notify("ViewObject", self.out_urn, "Completed DownloadDirectory")
