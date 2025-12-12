#!/usr/bin/env python
"""Flows for getting information about memory size."""
import re

from google.protobuf import any_pb2
from google.protobuf import wrappers_pb2
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import flows_pb2
from grr_response_proto import signed_commands_pb2
from grr_response_server import data_store
from grr_response_server import flow_base
from grr_response_server import flow_responses
from grr_response_server import rrg_stubs
from grr_response_server import server_stubs
from grr_response_proto.rrg import os_pb2 as rrg_os_pb2
from grr_response_proto.rrg.action import execute_signed_command_pb2 as rrg_execute_signed_command_pb2
from grr_response_proto.rrg.action import grep_file_contents_pb2 as rrg_grep_file_contents_pb2
from grr_response_proto.rrg.action import query_wmi_pb2 as rrg_query_wmi_pb2


class GetMemorySizeResult(rdf_structs.RDFProtoStruct):
  """RDF wrapper for the GetMemorySizeResult` message."""

  protobuf = flows_pb2.GetMemorySizeResult
  rdf_deps = []


class GetMemorySize(
    flow_base.FlowBase[
        flows_pb2.EmptyFlowArgs,
        flows_pb2.DefaultFlowStore,
        flows_pb2.DefaultFlowProgress,
    ]
):
  """Flow that gets size of the RAM available on the endpoint."""

  category = "/Collectors/"
  behaviours = flow_base.BEHAVIOUR_DEBUG

  result_types = [GetMemorySizeResult]
  proto_result_types = [flows_pb2.GetMemorySizeResult]

  only_protos_allowed = True

  def Start(self) -> None:
    if self.rrg_support and self.rrg_os_type == rrg_os_pb2.LINUX:
      action = rrg_stubs.GrepFileContents()
      action.args.path.raw_bytes = "/proc/meminfo".encode("utf-8")
      action.args.regex = "^MemTotal:.*$"
      action.Call(self._ProcessLinuxMeminfo)
    elif self.rrg_support and self.rrg_os_type == rrg_os_pb2.WINDOWS:
      action = rrg_stubs.QueryWmi()
      action.args.query = """
      SELECT TotalPhysicalMemory
        FROM Win32_ComputerSystem
      """
      action.Call(self._ProcessWindowsWin32ComputerSystem)
    elif self.rrg_support and self.rrg_os_type == rrg_os_pb2.MACOS:
      signed_command = data_store.REL_DB.ReadSignedCommand(
          "sysctl_hw_memsize",
          operating_system=signed_commands_pb2.SignedCommand.OS.MACOS,
      )

      action = rrg_stubs.ExecuteSignedCommand()
      action.args.command = signed_command.command
      action.args.command_ed25519_signature = signed_command.ed25519_signature
      action.args.timeout.seconds = 10
      action.Call(self._ProcessMacosSysctlHwMemsize)
    else:
      self.CallClientProto(
          server_stubs.GetMemorySize,
          next_state=self._ProcessGetMemorySize.__name__,
      )

  @flow_base.UseProto2AnyResponses
  def _ProcessLinuxMeminfo(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    if not responses.success:
      raise flow_base.FlowError(
          f"Failed to read from '/proc/meminfo': {responses.status}",
      )

    if len(responses) != 1:
      raise flow_base.FlowError(
          f"Unexpected number of responses: {len(responses)}",
      )

    response = rrg_grep_file_contents_pb2.Result()
    response.ParseFromString(list(responses)[0].value)

    content = response.content

    match = re.search(r"^MemTotal:\s+(?P<size>\d+)\s+(?P<unit>\w*)", content)
    if match is None:
      raise flow_base.FlowError(
          f"Unexpected format of the `/proc/meminfo` entry: {content}",
      )

    result = flows_pb2.GetMemorySizeResult()
    result.total_bytes = int(match["size"])

    if match["unit"] == "kB":
      # https://superuser.com/questions/1737654/what-is-the-true-meaning-of-the-unit-kb-in-proc-meminfo
      result.total_bytes *= 1024
    elif not match["unit"]:
      # No unit, we leave bytes as is. This should generally not happen, but we
      # handle this just to be on the safe side.
      pass
    else:
      # We allow there to be either no unit or `kB`, for everything else we just
      # fail hard. In practice, it should be always `kB` but it is better to be
      # covered and have error reporting in case this ever changes.
      raise flow_base.FlowError(
          f"Unexpected unit: {match['unit']}",
      )

    self.SendReplyProto(result)

  @flow_base.UseProto2AnyResponses
  def _ProcessWindowsWin32ComputerSystem(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    if not responses.success:
      raise flow_base.FlowError(
          f"Failed to query WMI `Win32_ComputerSystem`: {responses.status}",
      )

    if len(responses) != 1:
      raise flow_base.FlowError(
          f"Unexpected number of responses: {len(responses)}",
      )

    response = rrg_query_wmi_pb2.Result()
    response.ParseFromString(list(responses)[0].value)

    if "TotalPhysicalMemory" not in response.row:
      raise flow_base.FlowError(
          f"Row {response!r} missing 'TotalPhysicalMemory' column",
      )

    result = flows_pb2.GetMemorySizeResult()
    result.total_bytes = response.row["TotalPhysicalMemory"].uint

    self.SendReplyProto(result)

  @flow_base.UseProto2AnyResponses
  def _ProcessMacosSysctlHwMemsize(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    if not responses.success:
      raise flow_base.FlowError(
          f"Failed to execute `sysctl`: {responses.status}",
      )

    if len(responses) != 1:
      raise flow_base.FlowError(
          f"Unexpected number of responses: {len(responses)}",
      )

    response = rrg_execute_signed_command_pb2.Result()
    response.ParseFromString(list(responses)[0].value)

    if response.exit_code != 0:
      raise flow_base.FlowError(
          f"`sysctl` exit abnormally (code: {response.exit_code}, "
          f"stdout: {response.stdout}, stderr: {response.stderr})",
      )

    result = flows_pb2.GetMemorySizeResult()
    result.total_bytes = int(response.stdout.decode("ascii"))

    self.SendReplyProto(result)

  @flow_base.UseProto2AnyResponses
  def _ProcessGetMemorySize(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ):
    if not responses.success:
      raise flow_base.FlowError(
          f"Failed to obtain memory size: {responses.status}",
      )

    if len(responses) != 1:
      raise flow_base.FlowError(
          f"Unexpected number of responses: {len(responses)}",
      )

    # `GetMemorySize` ClientAction returns an `rdfvalue.ByteSize` (primitive).
    # This is then packed into a wrapper `config_pb2.Int64Value` in
    # `FlowResponseForLegacyResponse`.
    # TODO: Remove this workaround for the uint64 mapping when
    # no more ClientActions return RDFPrimitives.
    response = wrappers_pb2.Int64Value()
    response.ParseFromString(list(responses)[0].value)

    result = flows_pb2.GetMemorySizeResult()
    result.total_bytes = response.value

    self.SendReplyProto(result)
