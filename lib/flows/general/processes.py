#!/usr/bin/env python
# Copyright 2010 Google Inc.
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


"""These are process related flows."""


import time

from grr.lib import aff4
from grr.lib import flow
from grr.lib import utils
from grr.proto import jobs_pb2


class ListProcesses(flow.GRRFlow):
  """List running processes on a system."""

  category = "/Processes/"
  out_protobuf = jobs_pb2.URN

  @flow.StateHandler(next_state=["StoreProcessList"])
  def Start(self):
    """Start processing."""
    self.CallClient("ListProcesses", next_state="StoreProcessList")

  @flow.StateHandler()
  def StoreProcessList(self, responses):
    """This stores the processes."""

    if not responses.success:
      # Check for error, but continue. Errors are common on client.
      raise flow.FlowError("Error during process listing %s" % responses.status)

    urn = aff4.ROOT_URN.Add(self.client_id).Add("processes")
    process_fd = aff4.FACTORY.Create(urn, "ProcessListing", token=self.token)
    plist = process_fd.Schema.PROCESSES()

    proc_count = len(responses)
    for response in responses:
      plist.Append(response)

    process_fd.AddAttribute(plist)
    process_fd.Close()

    self.SendReply(jobs_pb2.URN(urn=utils.SmartUnicode(urn)))

    self.Notify("ViewObject", urn, "Listed %d Processes" % proc_count)


class GetProcessesBinaries(flow.GRRFlow):
  """Get binaries of all the processes running on a system."""

  category = "/Processes/"

  def __init__(self, output="analysis/get-processes-binaries/{u}-{t}",
               **kwargs):
    """Constructor.

    This flow exexutes ListProcesses flow and fetches binary for every process
    in the list.

    Args:
      output: Pattern used to generate a name for the output collection.
    """
    flow.GRRFlow.__init__(self, **kwargs)

    output = output.format(t=time.time(), u=self.user)
    self.output = aff4.ROOT_URN.Add(self.client_id).Add(output)
    self.fd = aff4.FACTORY.Create(self.output, "AFF4Collection", mode="w",
                                  token=self.token)
    self.fd.Set(self.fd.Schema.DESCRIPTION("GetProcessesBinaries process list"))
    self.collection_list = self.fd.Schema.COLLECTION()

  @flow.StateHandler(next_state="IterateProcesses")
  def Start(self):
    """Start processing, request processes list."""
    self.CallFlow("ListProcesses", next_state="IterateProcesses")

  @flow.StateHandler(next_state="HandleDownloadedFiles")
  def IterateProcesses(self, responses):
    """Load list of processes and start binaries-fetching flows.

    This state handler opens the URN returned from the parent flow, loads
    the list of processes from there, filters out processes without
    exe attribute and initiates GetFile flows for all others.

    Args:
      responses: jobs_pb2.URN pointing at ProcessListing file.
    """
    if not responses or not responses.success:
      raise flow.FlowErrow("ListProcesses flow failed %s", responses.status)

    urn = responses.First().urn
    self.Log("Response from ListProcesses flow: %s", urn)

    # Load processes list from the URN returned from the ListProcesses flow.
    process_fd = aff4.FACTORY.Open(urn, "ProcessListing", token=self.token)
    plist = process_fd.Get(process_fd.Schema.PROCESSES)

    # Filter out processes entries without "exe" attribute and
    # deduplicate the list.
    paths_to_fetch = sorted(set([p.exe for p in plist if p.exe]))

    self.Log("Got %d processes, fetching binaries for %d...", len(plist),
             len(paths_to_fetch))

    for p in paths_to_fetch:
      self.CallFlow("GetFile",
                    next_state="HandleDownloadedFiles",
                    path=p,
                    request_data={"path": p})

  @flow.StateHandler(jobs_pb2.StatResponse)
  def HandleDownloadedFiles(self, responses):
    """Handle success/failure of the GetFile flow."""
    if responses.success:
      for response_stat in responses:
        self.Log("Downloaded %s", response_stat.pathspec)
        self.collection_list.Append(response_stat)
    else:
      self.Log("Download of file %s failed %s",
               responses.request_data["path"], responses.status)

  @flow.StateHandler()
  def End(self):
    """Save the results collection and update the notification line."""
    self.fd.Set(self.collection_list)
    self.fd.Close()

    num_files = len(self.collection_list)
    self.Notify("ViewObject", self.output,
                "GetProcessesBinaries completed. "
                "Fetched {0:d} files".format(num_files))
