#!/usr/bin/env python
"""These are process related flows."""


import time

from grr.lib import aff4
from grr.lib import flow
from grr.lib import rdfvalue
from grr.proto import flows_pb2


class ListProcesses(flow.GRRFlow):
  """List running processes on a system."""

  category = "/Processes/"

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

    out_urn = self.client_id.Add("processes")
    process_fd = aff4.FACTORY.Create(out_urn, "ProcessListing",
                                     token=self.token)
    plist = process_fd.Schema.PROCESSES()

    proc_count = len(responses)
    for response in responses:
      self.SendReply(response)
      plist.Append(response)

    process_fd.AddAttribute(plist)
    process_fd.Close()

    self.Notify("ViewObject", out_urn, "Listed %d Processes" % proc_count)


class GetProcessesBinariesArgs(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.GetProcessesBinariesArgs


class GetProcessesBinaries(flow.GRRFlow):
  """Get binaries of all the processes running on a system."""

  category = "/Processes/"
  args_type = GetProcessesBinariesArgs

  @flow.StateHandler(next_state="IterateProcesses")
  def Start(self):
    """Start processing, request processes list."""

    output = self.args.output.format(t=time.time(), u=self.state.context.user)
    self.state.Register("output", self.client_id.Add(output))
    self.state.Register("fd", aff4.FACTORY.Create(
        self.state.output, "AFF4Collection", mode="w", token=self.token))
    self.state.fd.Set(self.state.fd.Schema.DESCRIPTION(
        "GetProcessesBinaries processes list"))

    self.CallFlow("ListProcesses", next_state="IterateProcesses")

  @flow.StateHandler(next_state="HandleDownloadedFiles")
  def IterateProcesses(self, responses):
    """Load list of processes and start binaries-fetching flows.

    This state handler opens the URN returned from the parent flow, loads
    the list of processes from there, filters out processes without
    exe attribute and initiates FastGetFile flows for all others.

    Args:
      responses: rdfvalue.Stat pointing at ProcessListing file.
    """
    if not responses or not responses.success:
      raise flow.FlowErrow("ListProcesses flow failed %s", responses.status)

    # Filter out processes entries without "exe" attribute and
    # deduplicate the list.
    paths_to_fetch = sorted(set([p.exe for p in responses if p.exe]))

    self.Log("Got %d processes, fetching binaries for %d...", len(responses),
             len(paths_to_fetch))

    for p in paths_to_fetch:
      pathspec = rdfvalue.PathSpec(path=p,
                                   pathtype=rdfvalue.PathSpec.PathType.OS)
      self.CallFlow("FastGetFile",
                    next_state="HandleDownloadedFiles",
                    pathspec=pathspec,
                    request_data={"path": p})

  @flow.StateHandler()
  def HandleDownloadedFiles(self, responses):
    """Handle success/failure of the FastGetFile flow."""
    if responses.success:
      for response_stat in responses:
        self.Log("Downloaded %s", response_stat.pathspec)
        self.SendReply(response_stat)
        self.state.fd.Add(stat=response_stat, urn=response_stat.aff4path)
    else:
      self.Log("Download of file %s failed %s",
               responses.request_data["path"], responses.status)

  @flow.StateHandler()
  def End(self):
    """Save the results collection and update the notification line."""
    self.state.fd.Close()

    num_files = len(self.state.fd)
    self.Notify("ViewObject", self.state.output,
                "GetProcessesBinaries completed. "
                "Fetched {0:d} files".format(num_files))


class GetProcessesBinariesVolatilityArgs(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.GetProcessesBinariesVolatilityArgs


class GetProcessesBinariesVolatility(flow.GRRFlow):
  """Get list of all running binaries from Volatility and fetch them.

    This flow executes the "vad" Volatility plugin to get the list of all
    currently running binaries (including dynamic libraries). Then it fetches
    all the binaries it has found.

    There is a caveat regarding using the "vad" plugin to detect currently
    running executable binaries. The "Filename" member of the _FILE_OBJECT
    struct is not reliable:

      * Usually it does not include volume information: i.e.
        \\Windows\\some\\path. Therefore it's impossible to detect the actual
        volume where the executable is located.

      * If the binary is executed from a shared network volume, the Filename
        attribute is not descriptive enough to easily fetch the file.

      * If the binary is executed directly from a network location (without
        mounting the volume) Filename attribute will contain yet another
        form of path.

      * Filename attribute is not actually used by the system (it's probably
        there for debugging purposes). It can be easily overwritten by a rootkit
        without any noticeable consequences for the running system, but breaking
        our functionality as a result.

    Therefore this plugin's functionality is somewhat limited. Basically, it
    won't fetch binaries that are located on non-default volumes.

    Possible workaround (future work):
    * Find a way to map given address space into the filename on the filesystem.
    * Fetch binaries directly from memory by forcing page-ins first (via
      some debug userland-process-dump API?) and then reading the memory.
  """
  category = "/Processes/"
  args_type = GetProcessesBinariesVolatilityArgs

  @flow.StateHandler(next_state="FetchBinaries")
  def Start(self):
    """Request VAD data."""
    output = self.args.output.format(t=time.time(), u=self.state.context.user)
    self.state.Register("output", self.client_id.Add(output))
    self.state.Register("fd", aff4.FACTORY.Create(
        self.state.output, "AFF4Collection", mode="w", token=self.token))

    self.state.fd.Set(self.state.fd.Schema.DESCRIPTION(
        "GetProcessesBinariesVolatility binaries (regex: %s) " %
        self.args.filename_regex or "None"))

    self.args.request.plugins.Append("vad")
    self.CallClient("VolatilityAction", self.args.request,
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
    if self.args.filename_regex:
      binaries = filter(self.args.filename_regex.Match, binaries)
      self.Log("Applied filename regex. Will fetch %d files",
               len(binaries))

    for path in binaries:
      pathspec = rdfvalue.PathSpec(path=path,
                                   pathtype=rdfvalue.PathSpec.PathType.OS)

      self.CallFlow("FastGetFile",
                    next_state="HandleDownloadedFiles",
                    pathspec=pathspec,
                    request_data={"path": path})

  @flow.StateHandler()
  def HandleDownloadedFiles(self, responses):
    """Handle success/failure of the FastGetFile flow."""
    if responses.success:
      for response_stat in responses:
        self.SendReply(response_stat)
        self.Log("Downloaded %s", responses.request_data["path"])
        self.state.fd.Add(stat=response_stat, urn=response_stat.aff4path)
    else:
      self.Log("Download of file %s failed %s",
               responses.request_data["path"], responses.status)

  @flow.StateHandler()
  def End(self):
    """Save the results collection and update the notification line."""
    self.state.fd.Close()

    num_files = len(self.state.fd)
    self.Notify("ViewObject", self.state.output,
                "GetProcessesBinariesVolatility completed. "
                "Fetched {0:d} files".format(num_files))
