#!/usr/bin/env python
"""A module with the implementation of the flow listing named pipes."""
import logging
import re
from typing import Dict
from typing import Optional

from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import pipes_pb2
from grr_response_server import flow_base
from grr_response_server import flow_responses
from grr_response_server import server_stubs
from grr_response_server.flows.general import processes


class ListNamedPipesFlowArgs(rdf_structs.RDFProtoStruct):
  """An RDF wrapper for arguments of the flow listing named pipes."""

  protobuf = pipes_pb2.ListNamedPipesFlowArgs
  rdf_deps = []


class ListNamedPipesFlowResult(rdf_structs.RDFProtoStruct):
  """An RDF wrapper for results of the flow listing named pipes."""

  protobuf = pipes_pb2.ListNamedPipesFlowResult
  rdf_deps = [
      rdf_client.NamedPipe,
      rdf_client.Process,
  ]


class ListNamedPipesFlow(flow_base.FlowBase):
  """A flow mixin with logic listing named pipes."""

  friendly_name = "List named pipes"
  category = "/Processes/"
  behaviours = flow_base.BEHAVIOUR_BASIC

  args_type = ListNamedPipesFlowArgs
  result_types = [ListNamedPipesFlowResult]

  def Start(self) -> None:
    super().Start()

    if self.client_os != "Windows":
      raise flow_base.FlowError(f"Unsupported platform: {self.client_os}")

    self.CallClient(
        action_cls=server_stubs.ListNamedPipes,
        next_state=self.OnListNamedPipesResult.__name__)

  def OnListNamedPipesResult(
      self,
      responses: flow_responses.Responses[ListNamedPipesFlowArgs],
  ) -> None:
    """Handles results of the action listing named pipes."""
    if not responses.success:
      raise flow_base.FlowError(responses.status)

    pipe_name_regex = re.compile(self.args.pipe_name_regex)
    pipe_type_filter = self.args.pipe_type_filter
    pipe_end_filter = self.args.pipe_end_filter

    self.state.pipes = []
    pids = []

    for response in responses:
      if not isinstance(response, rdf_client.NamedPipe):
        logging.error("Unexpected response: %s", response)
        continue

      if not pipe_name_regex.search(response.name):
        continue

      if pipe_type_filter == pipes_pb2.ListNamedPipesFlowArgs.BYTE_TYPE:
        if response.flags & PIPE_TYPE != PIPE_TYPE_BYTE:
          continue
      elif pipe_type_filter == pipes_pb2.ListNamedPipesFlowArgs.MESSAGE_TYPE:
        if response.flags & PIPE_TYPE != PIPE_TYPE_MESSAGE:
          continue
      if pipe_end_filter == pipes_pb2.ListNamedPipesFlowArgs.CLIENT_END:
        if response.flags & PIPE_END != PIPE_CLIENT_END:
          continue
      elif pipe_end_filter == pipes_pb2.ListNamedPipesFlowArgs.SERVER_END:
        if response.flags & PIPE_END != PIPE_SERVER_END:
          continue

      self.state.pipes.append(response)

      if response.HasField("server_pid"):
        pids.append(response.server_pid)
      if response.HasField("client_pid"):
        pids.append(response.client_pid)

    self.CallFlow(
        flow_name=processes.ListProcesses.__name__,
        next_state=self.OnListProcessesResult.__name__,
        filename_regex=self.args.proc_exe_regex,
        pids=pids,
    )

  def OnListProcessesResult(
      self,
      responses: flow_responses.Responses[rdf_client.Process],
  ) -> None:
    if not responses.success:
      # Not that we don't want to fail hard if we fail to collect process data
      # as this is just supplementary information and we might still have some
      # pipe data to report to the user.
      self.Log("Failed to collect process information")

    procs_by_pid: Dict[int, rdf_client.Process] = {}

    for response in responses:
      if not isinstance(response, rdf_client.Process):
        logging.error("Unexpected response: %s", response)
        continue

      procs_by_pid[response.pid] = response

    for pipe in self.state.pipes:
      result = ListNamedPipesFlowResult()
      result.pipe = pipe

      pid: Optional[int] = None
      if pipe.HasField("server_pid"):
        pid = pipe.server_pid
      elif pipe.HasField("client_pid"):
        pid = pipe.client_pid

      if pid is not None:
        try:
          result.proc = procs_by_pid[pid]
        except KeyError:
          # In case there was a process executable regex specified, missing data
          # about the associated process is expected (no need to log anything)
          # and such pipes should be omitted from the results. If this regex has
          # not been specified but process information is missing, there might
          # be some issue (e.g. the process has been terminated between getting
          # the pipe data and process information) so it is better to leave some
          # trace to the user.
          if self.args.proc_exe_regex:
            continue
          else:
            self.Log("No process information for pid '%s'", pid)
      else:
        self.Log("No pid for pipe '%s'", pipe.name)

      self.SendReply(result)


# https://docs.microsoft.com/en-us/windows/win32/api/namedpipeapi/nf-namedpipeapi-getnamedpipeinfo
PIPE_TYPE_BYTE = 0x00000000
PIPE_TYPE_MESSAGE = 0x00000004
PIPE_CLIENT_END = 0x00000000
PIPE_SERVER_END = 0x00000001

PIPE_TYPE = PIPE_TYPE_BYTE | PIPE_TYPE_MESSAGE
PIPE_END = PIPE_CLIENT_END | PIPE_SERVER_END
