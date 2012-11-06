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
import re
import stat
import time

from grr.lib import aff4
from grr.lib import flow
from grr.lib import type_info
from grr.lib import utils
from grr.proto import jobs_pb2


class FindFiles(flow.GRRFlow):
  """Find files on the client.

  Returns to parent flow:
    jobs_pb2.StatResponse objects for each found file.
  """

  category = "/Filesystem/"
  flow_typeinfo = {"pathtype": type_info.ProtoEnum(jobs_pb2.Path, "PathType"),
                   "findspec": type_info.Proto(jobs_pb2.Find),
                   "output": type_info.StringOrNone()}

  out_protobuf = jobs_pb2.StatResponse

  def __init__(self, path="/",
               pathtype=jobs_pb2.Path.OS,
               filename_regex="", data_regex="",
               iterate_on_number=100, max_results=500,
               output="analysis/find/{u}-{t}",
               findspec=None, cross_devs=False, **kwargs):
    """This flow searches for files on the client.

    The result from this flow is an AFF4Collection which will be created on the
    output path, containing all aff4 objects on the client which match the
    criteria. Note that these files will not be downloaded by this flow, only
    the metadata of the file in fetched.

    Note: This flow is inefficient for collecting a large number of files.

    Args:
      path: Search recursively from this place.
      pathtype: Identifies requested path type. Enum from Path protobuf.
      filename_regex: A regular expression to match the filename (Note only the
           base component of the filename is matched).
      data_regex: The file data should match this regex.
      iterate_on_number: The total number of files to search before iterating on
           the server.
      max_results: Maximum number of results to get.
      output: The path to the output container for this find. Will be created
          under the client. supports format variables {u} and {t} for user and
          time. E.g. /analysis/find/{u}-{t}.
          If set to None, no collection will be created.
      findspec: A jobs_pb2.Find, if specified, other arguments are ignored.
      cross_devs: If True, the find action will descend into mounted devices.
    """
    flow.GRRFlow.__init__(self, **kwargs)

    if findspec:
      self.request = findspec
    else:
      pb = jobs_pb2.Path(path=path, pathtype=int(pathtype))
      self.request = jobs_pb2.Find(pathspec=pb, cross_devs=cross_devs,
                                   path_regex=filename_regex)
      if data_regex:
        self.request.data_regex = data_regex
      self.request.iterator.number = iterate_on_number

    self.request.iterator.number = min(max_results,
                                       self.request.iterator.number)
    # Check the regexes are valid.
    try:
      if self.request.data_regex:
        re.compile(self.request.data_regex)
      if self.request.path_regex:
        re.compile(self.request.path_regex)
    except re.error as e:
      raise RuntimeError("Invalid regex for FindFiles. Err: {0}".format(e))

    self.path = self.request.pathspec.path
    self.max_results = max_results
    self.received_count = 0

    if output:
      # Create the output collection and get it ready.
      output = output.format(t=time.time(), u=self.user)
      self.output = aff4.ROOT_URN.Add(self.client_id).Add(output)
      self.fd = aff4.FACTORY.Create(self.output, "AFF4Collection", mode="w",
                                    token=self.token)

      self.fd.Set(self.fd.Schema.DESCRIPTION("Find {0} -name {1}".format(
          path, filename_regex)))
      self.collection_list = self.fd.Schema.COLLECTION()

    else:
      self.output = None

    self.urn = aff4.ROOT_URN.Add(self.client_id)

  @flow.StateHandler(next_state="IterateFind")
  def Start(self, unused_response):
    """Issue the find request to the client."""
    # Build up the request protobuf.
    # Call the client with it
    self.CallClient("Find", self.request, next_state="IterateFind")

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
        self.collection_list.Append(response.hit)

      # Send the stat to the parent flow.
      self.SendReply(stat_response)

    self.received_count += len(responses)

    # Exit if we hit the max result count we wanted or we're finished.
    if (self.received_count < self.max_results and
        responses.iterator.state != jobs_pb2.Iterator.FINISHED):
      self.request.iterator.CopyFrom(responses.iterator)
      # If we are close to max_results reduce the iterator.
      self.request.iterator.number = min(self.request.iterator.number,
                                         self.max_results - self.received_count)
      self.CallClient("Find", self.request, next_state="IterateFind")
      self.Log("%d files processed.", self.received_count)

  @flow.StateHandler()
  def End(self):
    """Save the collection and notification if output is enabled."""
    if self.output:
      self.fd.Set(self.fd.Schema.COLLECTION, self.collection_list)
      self.fd.Close()

      self.Notify("ViewObject", self.output,
                  u"Found on {0} completed {1} hits".format(
                      len(self.collection_list), self.path))
