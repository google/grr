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

"""Find files on the client."""
import time

from grr.lib import aff4
from grr.lib import flow
from grr.lib import utils
from grr.proto import jobs_pb2


class FindFiles(flow.GRRFlow):
  """Find files on the client."""

  category = "/Filesystem/"

  def __init__(self, path="/", filename_regex="", data_regex="",
               number_of_results=100, output="", raw=True, **kwargs):
    """This flow searches for files on the client.

    The result from this flow is an AFF4Collection which will be created on the
    output path, containing all aff4 objects on the client which match the
    criteria. Note that these files will not be downloaded by this flow, only
    the metadata of the file in fetched.

    Args:
      path: Search recursively from this place.
      filename_regex: A regular expression to match the filename (Note only the
           base component of the filename is matched).
      data_regex: The file data should match this regex.
      number_of_results: The total number of files to search before iterating on
           the server.
      output: The path to the output container for this find. If blank uses a
           default value under /client_id/analysis/Find/.
      raw: Use raw files access.
      kwargs: passthrough.
    """
    flow.GRRFlow.__init__(self, **kwargs)

    self.path = path
    if raw:
      self._pathtype = jobs_pb2.Path.TSK
    else:
      self._pathtype = jobs_pb2.Path.OS
    self.filename_regex = filename_regex
    self.data_regex = data_regex
    self.number_of_results = number_of_results
    if not output:
      output = aff4.ROOT_URN.Add(self.client_id).Add(
          "analysis/Find/%s-%d" % (self.user, time.time()))

    self.output = aff4.RDFURN(output)
    self.urn = aff4.ROOT_URN.Add(self.client_id)

  @flow.StateHandler(next_state="IterateFind")
  def Start(self, unused_response):
    """Issue the find request to the client."""
    # Build up the request protobuf.
    pb = jobs_pb2.Path(path=self.path, pathtype=self._pathtype)
    self.request = jobs_pb2.Find(pathspec=pb, path_regex=self.filename_regex)
    if self.data_regex:
      self.request.data_regex = self.data_regex

    self.request.iterator.number = self.number_of_results
    self.directory_inode = aff4.FACTORY.RDFValue("DirectoryInode")()

    # Call the client with it
    self.CallClient("Find", self.request, next_state="IterateFind")

  @flow.StateHandler(next_state="IterateFind")
  def IterateFind(self, responses):
    """Iterate in this state until no more results are available."""
    if not responses.success:
      raise IOError(responses.status)

    for response in responses:
      # Create the file in the VFS
      vfs_urn = self.urn.Add(utils.PathspecToAff4(response.hit.pathspec))
      fd = aff4.FACTORY.Create(vfs_urn, "VFSFile")
      fd.Set(fd.Schema.STAT, aff4.FACTORY.RDFValue("StatEntry")(
          response.hit))
      fd.Set(fd.Schema.SIZE, aff4.RDFInteger(response.hit.st_size))
      fd.Close()

      response.hit.path = utils.SmartUnicode(vfs_urn)
      self.directory_inode.AddDirectoryEntry(response.hit)

    if responses.iterator.state != jobs_pb2.Iterator.FINISHED:
      self.request.iterator.CopyFrom(responses.iterator)
      self.CallClient("Find", self.request, next_state="IterateFind")

    else:
      fd = aff4.FACTORY.Create(self.output).Upgrade("AFF4Collection")
      fd.Set(fd.Schema.DIRECTORY, self.directory_inode)
      fd.Set(fd.Schema.DESCRIPTION, aff4.RDFString("Find %s -name %s" % (
            self.path, self.filename_regex)))

      view = fd.Schema.VIEW()

      fd.Set(fd.Schema.VIEW, view)

      fd.Close()
