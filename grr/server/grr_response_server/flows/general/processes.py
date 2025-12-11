#!/usr/bin/env python
"""These are process related flows."""
import re

from google.protobuf import any_pb2
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import standard as rdf_standard
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_proto import sysinfo_pb2
from grr_response_server import flow_base
from grr_response_server import flow_responses
from grr_response_server import server_stubs
from grr_response_server.flows.general import file_finder


class ListProcessesArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.ListProcessesArgs
  rdf_deps = [
      rdf_standard.RegularExpression,
  ]


class ListProcesses(
    flow_base.FlowBase[
        flows_pb2.ListProcessesArgs,
        flows_pb2.DefaultFlowStore,
        flows_pb2.DefaultFlowProgress,
    ]
):
  """List running processes on a system."""

  category = "/Processes/"
  behaviours = flow_base.BEHAVIOUR_BASIC
  args_type = ListProcessesArgs
  result_types = (rdf_client.Process, rdf_client_fs.StatEntry)

  proto_args_type = flows_pb2.ListProcessesArgs
  proto_result_types = (sysinfo_pb2.Process, jobs_pb2.StatEntry)
  only_protos_allowed = True

  def Start(self):
    """Start processing."""
    self.CallClientProto(
        server_stubs.ListProcesses, next_state=self.IterateProcesses.__name__
    )

  def _FilenameMatch(self, process: sysinfo_pb2.Process) -> bool:
    if not self.proto_args.filename_regex:
      return True
    return re.compile(self.proto_args.filename_regex).match(process.exe)

  def _ConnectionStateMatch(self, process: sysinfo_pb2.Process) -> bool:
    if not self.proto_args.connection_states:
      return True

    for connection in process.connections:
      if connection.state in self.args.connection_states:
        return True
    return False

  @flow_base.UseProto2AnyResponses
  def IterateProcesses(
      self, responses_any: flow_responses.Responses[any_pb2.Any]
  ) -> None:
    """This stores the processes."""

    if not responses_any.success:
      # Check for error, but continue. Errors are common on client.
      raise flow_base.FlowError(
          "Error during process listing %s" % responses_any.status
      )

    responses = []
    for response_any in responses_any:
      response = sysinfo_pb2.Process()
      response_any.Unpack(response)
      responses.append(response)

    if self.proto_args.pids:
      pids = set(self.proto_args.pids)
      responses = [p for p in responses if p.pid in pids]

    if self.proto_args.fetch_binaries:
      # Filter out processes entries without "exe" attribute and
      # deduplicate the list.
      paths_to_fetch = set()
      for p in responses:
        if p.exe and self._FilenameMatch(p) and self._ConnectionStateMatch(p):
          paths_to_fetch.add(p.exe)
      paths_to_fetch = sorted(paths_to_fetch)

      self.Log(
          "Got %d processes, fetching binaries for %d...",
          len(responses),
          len(paths_to_fetch),
      )

      self.CallFlowProto(
          file_finder.ClientFileFinder.__name__,
          flow_args=flows_pb2.FileFinderArgs(
              paths=paths_to_fetch,
              action=flows_pb2.FileFinderAction(
                  action_type=flows_pb2.FileFinderAction.Action.DOWNLOAD
              ),
          ),
          next_state=self.HandleDownloadedFiles.__name__,
      )

    else:
      # Only send the list of processes if we don't fetch the binaries
      skipped = 0
      for p in responses:
        # It's normal to have lots of sleeping processes with no executable path
        # associated.
        if p.exe:
          if self._FilenameMatch(p) and self._ConnectionStateMatch(p):
            self.SendReplyProto(p)
        else:
          if self.args.connection_states:
            if self._ConnectionStateMatch(p):
              self.SendReplyProto(p)
          else:
            skipped += 1

      if skipped:
        self.Log("Skipped %s entries, missing path for regex" % skipped)

  @flow_base.UseProto2AnyResponses
  def HandleDownloadedFiles(
      self, responses: flow_responses.Responses[any_pb2.Any]
  ) -> None:
    """Handle success/failure of the FileFinder flow."""
    if not responses.success:
      self.Log(
          "Download of file %s failed %s",
          responses.request_data["path"],
          responses.status,
      )

    for response_any in responses:
      response = flows_pb2.FileFinderResult()
      response_any.Unpack(response)

      self.Log("Downloaded %s", response.stat_entry.pathspec)
      self.SendReplyProto(response.stat_entry)
