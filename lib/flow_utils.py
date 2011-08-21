#!/usr/bin/env python
#
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


"""Utils for flow related tasks."""



import stat


import logging
from grr.lib import aff4
from grr.lib import flow
from grr.proto import jobs_pb2


class DownloadDirectory(flow.GRRFlow):
  """Flow for recursively downloading all files in a directory."""

  category = "/Filesystem/"

  def __init__(self, path="/", depth=10,
               ignore_errors=False, raw=True, **kwargs):
    """Constructor.

    Args:
      path: The directory path to download.
      depth: Maximum recursion depth.
      ignore_errors: If True, we do not raise an error in the case
                     that a directory or file cannot be not found.
      raw: Use raw file access.

    """
    self._path = path
    self._depth = depth
    self._ignore_errors = ignore_errors
    self._raw = raw
    if raw:
      self._ptype = jobs_pb2.Path.TSK
    else:
      self._ptype = jobs_pb2.Path.OS
    flow.GRRFlow.__init__(self, **kwargs)

  @flow.StateHandler(next_state="DownloadDir")
  def Start(self, unused_response):
    """Issue a request to list the directory."""
    self.urn = aff4.ROOT_URN.Add(self.client_id)
    # We use data to pass the path to the callback:
    p = jobs_pb2.Path(path=self._path, pathtype=self._ptype)
    self.CallClient("ListDirectory", pathspec=p, next_state="DownloadDir",
                    request_data=dict(depth=self._depth, path=self._path))

  @flow.StateHandler(next_state=["DownloadDir", "Done"])
  def DownloadDir(self, responses):
    """Download all files in a given directory recursively."""

    if not responses.success:
      if not self._ignore_errors:
        err = "Error downloading directory: %s" % responses.request_data["path"]
        logging.error(err)
        raise flow.FlowError(err)
    else:
      depth = responses.request_data["depth"] - 1
      if depth < 1:
        # max recursion depth reached
        return
      for handle in responses:
        if stat.S_ISDIR(handle.st_mode):
          p = jobs_pb2.Path()
          p.CopyFrom(handle.pathspec)
          self.CallClient("ListDirectory", next_state="DownloadDir",
                          pathspec=p, request_data=dict(depth=depth,
                                                        path=handle.path))
        else:
          if stat.S_ISREG(handle.st_mode):
            self.CallFlow("GetFile", path=handle.pathspec.path,
                          pathtype=handle.pathspec.pathtype, next_state="Done",
                          request_data=dict(path=handle.pathspec.path))

  @flow.StateHandler()
  def Done(self, responses):
    if not responses.success:
      if not self._ignore_errors:
        err = "Error downloading file %s" % responses.request_data["path"]
        logging.error(err)
        raise flow.FlowError(err)


def GetHomedirPath(client, user, domain=None):
  """Get a path to a users home directory.

  Args:
    client: Client ID as a string (e.g. "C.2f34cb70a2ae4c35").
    user: Username as string.
    domain: User's domain (if applicable).

  Returns:
    A string containing the path to the user's home directory.

  Raises:
    OSError: On invalid system in the Schema.
  """
  fd = aff4.FACTORY.Open(aff4.ROOT_URN.Add(client), mode="r")

  users = [u for u in fd.Get(fd.Schema.USER) if u.username == user]

  if domain:
    users = [u for u in users if u.domain == domain]

  if not users:
    return ""

  hd = users[0].homedir

  return hd
