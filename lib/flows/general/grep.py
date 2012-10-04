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


"""A simple grep flow."""



import time

from grr.lib import aff4
from grr.lib import flow
from grr.lib import type_info
from grr.lib import utils
from grr.proto import jobs_pb2


class Grep(flow.GRRFlow):
  """A simple grep flow."""

  category = "/Filesystem/"
  flow_typeinfo = {"pathtype": type_info.ProtoEnum(jobs_pb2.Path, "PathType"),
                   "mode": type_info.ProtoEnum(jobs_pb2.GrepRequest, "Mode")}

  out_protobuf = jobs_pb2.BufferReadMessage

  XOR_IN_KEY = 37
  XOR_OUT_KEY = 57

  def __init__(self, path="/",
               pathtype=jobs_pb2.Path.OS,
               grep_regex=None, grep_literal=None,
               offset=0, length=10*1024*1024*1024,
               mode=jobs_pb2.GrepRequest.ALL_HITS,
               bytes_before=10, bytes_after=10,
               output="analysis/grep/{u}-{t}", **kwargs):
    """This flow greps a file on the client for a pattern or a regex.

    Args:
      path: A path to the file.
      pathtype: Identifies requested path type. Enum from Path protobuf.
      grep_regex: The file data should match this regex.
      grep_literal: The file data should contain this pattern. Only one
                    parameter of grep_regex and grep_literal should be set.
      offset: An offset in the file to start grepping from.
      length: The maximum number of bytes this flow will look at.
      mode: Should this grep return all hits or just the first.
      bytes_before: The number of data bytes to return before each hit.
      bytes_after: The number of data bytes to return after each hit.
      output: The path to the output container for this find. Will be created
          under the client. supports format variables {u} and {t} for user and
          time. E.g. /analysis/grep/{u}-{t}.
    """

    super(Grep, self).__init__(**kwargs)

    self.request = jobs_pb2.GrepRequest(
        start_offset=offset,
        length=length,
        mode=mode,
        bytes_before=bytes_before,
        bytes_after=bytes_after,
        xor_in_key=self.XOR_IN_KEY,
        xor_out_key=self.XOR_OUT_KEY)

    if grep_literal:
      self.request.literal = utils.Xor(utils.SmartStr(grep_literal),
                                       self.XOR_IN_KEY)

    if grep_regex:
      self.request.regex = grep_regex

    target = jobs_pb2.Path(path=path, pathtype=pathtype)
    self.request.target.MergeFrom(target)
    self.output = output

  @flow.StateHandler(next_state=["StoreResults"])
  def Start(self):
    self.CallClient("Grep", self.request, next_state="StoreResults")

  @flow.StateHandler()
  def StoreResults(self, responses):
    if responses.success:
      output = self.output.format(t=time.time(), u=self.user)
      output_urn = aff4.ROOT_URN.Add(self.client_id).Add(output)

      fd = aff4.FACTORY.Create(output_urn, "GrepResults", mode="rw",
                               token=self.token)

      if self.request.HasField("literal"):
        self.request.literal = utils.Xor(self.request.literal,
                                         self.XOR_IN_KEY)
      fd.Set(fd.Schema.DESCRIPTION("Grep by %s: %s" % (
          self.user, str(self.request))))
      hits = fd.Get(fd.Schema.HITS)

      for response in responses:
        response.data = utils.Xor(response.data,
                                  self.XOR_OUT_KEY)
        response.length = len(response.data)
        hits.Append(response)

      fd.Set(fd.Schema.HITS, hits)
      fd.Close()
    else:
      self.Log("Error grepping file: %s.", responses.status)
