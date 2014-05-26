#!/usr/bin/env python
"""These are process related flows."""


from grr.lib import flow
from grr.lib import rdfvalue
from grr.proto import flows_pb2


class ListProcessesArgs(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.ListProcessesArgs


class ListProcesses(flow.GRRFlow):
  """List running processes on a system."""

  category = "/Processes/"
  behaviours = flow.GRRFlow.behaviours + "BASIC"
  args_type = ListProcessesArgs

  @flow.StateHandler(next_state=["IterateProcesses"])
  def Start(self):
    """Start processing."""
    self.CallClient("ListProcesses", next_state="IterateProcesses")

  @flow.StateHandler(next_state="HandleDownloadedFiles")
  def IterateProcesses(self, responses):
    """This stores the processes."""

    if not responses.success:
      # Check for error, but continue. Errors are common on client.
      raise flow.FlowError("Error during process listing %s" % responses.status)

    if self.args.fetch_binaries:
      # Filter out processes entries without "exe" attribute and
      # deduplicate the list.
      paths_to_fetch = set()
      for p in responses:
        if p.exe and self.args.filename_regex.Match(p.exe):
          paths_to_fetch.add(p.exe)
      paths_to_fetch = sorted(paths_to_fetch)

      self.Log("Got %d processes, fetching binaries for %d...", len(responses),
               len(paths_to_fetch))

      self.CallFlow("FileFinder",
                    paths=paths_to_fetch,
                    action=rdfvalue.FileFinderAction(
                        action_type=rdfvalue.FileFinderAction.Action.DOWNLOAD),
                    next_state="HandleDownloadedFiles")

    else:
      # Only send the list of processes if we don't fetch the binaries
      for response in responses:
        self.SendReply(response)

  @flow.StateHandler()
  def HandleDownloadedFiles(self, responses):
    """Handle success/failure of the FileFinder flow."""
    if responses.success:
      for response in responses:
        self.Log("Downloaded %s", response.stat_entry.pathspec)
        self.SendReply(response.stat_entry)

    else:
      self.Log("Download of file %s failed %s",
               responses.request_data["path"], responses.status)

  @flow.StateHandler()
  def End(self):
    """Save the results collection and update the notification line."""
    if self.runner.output is not None:
      num_items = len(self.runner.output)
      if self.args.fetch_binaries:
        self.Notify("ViewObject", self.runner.output.urn,
                    "ListProcesses completed. "
                    "Fetched {0:d} files".format(num_items))
      else:
        self.Notify("ViewObject", self.runner.output.urn,
                    "ListProcesses completed. "
                    "Listed {0:d} processes".format(num_items))
