#!/usr/bin/env python
"""These are process related flows."""


import re
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

    self.SendReply(urn)

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
    self.fd.Set(self.fd.Schema.DESCRIPTION(
        "GetProcessesBinaries processes list"))
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
    exe attribute and initiates FastGetFile flows for all others.

    Args:
      responses: jobs_pb2.URN pointing at ProcessListing file.
    """
    if not responses or not responses.success:
      raise flow.FlowErrow("ListProcesses flow failed %s", responses.status)

    urn = responses.First()
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
      # Sending reply with an expected file URN - this may be useful if this
      # flow is used as a nested flow.
      file_urn = aff4.AFF4Object.VFSGRRClient.PathspecToURN(
          utils.Pathspec(path=p, pathtype=jobs_pb2.Path.OS), self.client_id)
      self.SendReply(file_urn)

      self.CallFlow("FastGetFile",
                    next_state="HandleDownloadedFiles",
                    path=p,
                    request_data={"path": p})

  @flow.StateHandler(jobs_pb2.StatResponse)
  def HandleDownloadedFiles(self, responses):
    """Handle success/failure of the FastGetFile flow."""
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


class GetProcessesBinariesVolatility(flow.GRRFlow):
  """Get list of all running binaries from Volatility and fetch them."""

  category = "/Processes/"

  def __init__(self,
               output="analysis/get-processes-binaries-volatility/{u}-{t}",
               devicepath=r"\\.\pmem",
               profile=None,
               filename_regex="",
               **kwargs):
    """Constructor.

    This flow executes "vad" Volatility plugin to get the list of all
    currently running binaries (including dynamic libraries). Then it
    fetches all the binaries it has found.

    There is a caveat regarding using the "vad" plugin to detect currently
    running executable binaries. "Filename" memory area attribute that we use
    is not reliable:
      * Usually it does not include volume information: i.e.
        \\Windows\\some\\path. Therefore it's impossible to detect the actual
        volume where executable is located.
      * If the binary is executed from a shared volume of the network, the
        Filename attribute is not descriptive enough to easily fetch the file.
      * If the binary is executed directly from a network location (without
        mounting the volume) Filename attribute will contain yet another
        form of path.
      * Filename attribute is not actually used by the system (it's probably
        there for debugging purposes). It can be easily overwritten by the
        rootkit without any noticeable consequences for the running system,
        but breaking our functionality as a result.

    Therefore this plugin's functionality is somewhat limited. Basically, it
    won't fetch binaries that are located on non-default volume.

    Possible workaround (future work):
    * Find a way to map given address space into the filename on the filesystem.
    * Fetch binaries directly from memory by forcing page-ins first (via
      some debug userland-process-dump API?) and then reading the memory.

    Args:
      output: Pattern used to generate a name for the output collection.
      devicepath: Device path used by Volatility.
      profile: Profile used by Volatility.
      filename_regex: Regex used to filter the list of binaries to download.
    """
    super(GetProcessesBinariesVolatility, self).__init__(**kwargs)

    output = output.format(t=time.time(), u=self.user)
    self.output = aff4.ROOT_URN.Add(self.client_id).Add(output)
    self.fd = aff4.FACTORY.Create(self.output, "AFF4Collection", mode="w",
                                  token=self.token)
    self.fd.Set(self.fd.Schema.DESCRIPTION(
        "GetProcessesBinariesVolatility binaries (regex: %s) " %
        filename_regex or "None"))
    self.collection_list = self.fd.Schema.COLLECTION()

    device = jobs_pb2.Path(path=devicepath, pathtype=jobs_pb2.Path.MEMORY)
    self.request = jobs_pb2.VolatilityRequest(device=device)
    self.request.plugins.append("vad")
    if profile:
      self.request.profile = profile
    self.filename_regex = re.compile(filename_regex or ".")

  @flow.StateHandler(next_state="FetchBinaries")
  def Start(self):
    """Request VAD data."""
    self.CallClient("VolatilityAction", self.request,
                    next_state="FetchBinaries")

  @flow.StateHandler(next_state="HandleDownloadedFiles")
  def FetchBinaries(self, responses):
    """Parses Volatility response and initiates FastGetFile flows."""
    if not responses.success:
      self.Log("Error fetching VAD data: %s", responses.status)
      return

    binaries = set()

    # Collect binaries list from VolatilityResponse. We search for tables that
    # have "protection" and "filename" columns.
    # TODO(user): create an RDFProto class to reuse the functionality below.
    for response in responses:
      for section in response.sections:
        table = section.table

        # Find indices of "protection" and "filename" columns
        indexed_headers = dict([(header.name, i)
                                for i, header in enumerate(table.headers)])
        try:
          protection_col_index = indexed_headers["protection"]
          filename_col_index = indexed_headers["filename"]
        except KeyError:
          # If we can't find "protection" and "filename" columns, just skip
          # this section
          continue

        for row in table.rows:
          protection_attr = row.values[protection_col_index]
          filename_attr = row.values[filename_col_index]

          if protection_attr.svalue in ("EXECUTE_READ",
                                        "EXECUTE_READWRITE",
                                        "EXECUTE_WRITECOPY"):
            if filename_attr.svalue:
              binaries.add(filename_attr.svalue)

    self.Log("Found %d binaries", len(binaries))
    if self.filename_regex:
      binaries = filter(self.filename_regex.match, binaries)
      self.Log("Applied filename regex. Will fetch %d files",
               len(binaries))

    for path in binaries:
      # Sending reply with an expected file URN - this may be useful if this
      # flow is used as a nested flow.
      file_urn = aff4.AFF4Object.VFSGRRClient.PathspecToURN(
          utils.Pathspec(path=path, pathtype=jobs_pb2.Path.OS), self.client_id)
      self.SendReply(file_urn)

      self.CallFlow("FastGetFile",
                    next_state="HandleDownloadedFiles",
                    path=path,
                    request_data={"path": path})

  @flow.StateHandler(jobs_pb2.StatResponse)
  def HandleDownloadedFiles(self, responses):
    """Handle success/failure of the FastGetFile flow."""
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
                "GetProcessesBinariesVolatility completed. "
                "Fetched {0:d} files".format(num_files))
