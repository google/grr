#!/usr/bin/env python
"""Flows related to CrowdStrike security software."""

import binascii
import re

from google.protobuf import any_pb2
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import crowdstrike_pb2
from grr_response_proto import jobs_pb2
from grr_response_proto import signed_commands_pb2
from grr_response_server import data_store
from grr_response_server import flow_base
from grr_response_server import flow_responses
from grr_response_server import rrg_stubs
from grr_response_server import server_stubs
from grr_response_server.models import blobs as models_blobs
from grr_response_proto.rrg import os_pb2 as rrg_os_pb2
from grr_response_proto.rrg import winreg_pb2 as rrg_winreg_pb2
from grr_response_proto.rrg.action import execute_signed_command_pb2 as rrg_execute_signed_command_pb2
from grr_response_proto.rrg.action import get_file_contents_pb2 as rrg_get_file_contents_pb2
from grr_response_proto.rrg.action import get_winreg_value_pb2 as rrg_get_winreg_value_pb2


class GetCrowdstrikeAgentIdResult(rdf_structs.RDFProtoStruct):
  protobuf = crowdstrike_pb2.GetCrowdstrikeAgentIdResult
  rdf_deps = []


class GetCrowdStrikeAgentID(flow_base.FlowBase):
  """Flow that retrieves the identifier of the CrowdStrike agent."""

  friendly_name = "Get CrowdStrike agent identifier"
  category = "/Collectors/"

  result_types = (GetCrowdstrikeAgentIdResult,)
  proto_result_types = (crowdstrike_pb2.GetCrowdstrikeAgentIdResult,)

  def Start(self) -> None:
    if self.rrg_support:
      if self.rrg_os_type == rrg_os_pb2.LINUX:
        return self._StartRRGLinux()
      if self.rrg_os_type == rrg_os_pb2.WINDOWS:
        return self._StartRRGWindows()
      if self.rrg_os_type == rrg_os_pb2.MACOS:
        return self._StartRRGMacOS()

    if self.client_os == "Linux":
      return self._StartLinux()
    elif self.client_os == "Windows":
      return self._StartWindows()
    elif self.client_os == "Darwin":
      return self._StartMacOS()
    else:
      raise flow_base.FlowError(f"Unexpected system: {self.client_os}")

  def _StartRRGLinux(self) -> None:
    assert data_store.REL_DB is not None

    command = data_store.REL_DB.LookupSignedCommand(
        operating_system=signed_commands_pb2.SignedCommand.LINUX,
        path="/opt/CrowdStrike/falconctl",
        args=["-g", "--cid", "--aid"],
    )

    action = rrg_stubs.ExecuteSignedCommand()
    action.args.command = command.command
    action.args.command_ed25519_signature = command.ed25519_signature
    action.args.timeout.seconds = 5
    action.Call(self._OnLinuxRRGResponse)

  def _StartLinux(self) -> None:
    args = jobs_pb2.ExecuteRequest()
    args.cmd = "/opt/CrowdStrike/falconctl"
    args.args.extend(["-g", "--cid", "--aid"])

    self.CallClientProto(
        server_stubs.ExecuteCommand,
        args,
        next_state=self._OnLinuxResponse.__name__,
    )

  def _StartRRGWindows(self) -> None:
    action = rrg_stubs.GetWinregValue()
    action.args.root = rrg_winreg_pb2.LOCAL_MACHINE
    action.args.key = r"SYSTEM\CurrentControlSet\Services\CSAgent\Sim"
    action.args.name = "AG"
    action.Call(self._OnWindowsRRGResponse)

  def _StartWindows(self) -> None:
    # TODO: There is no dedicated action for obtaining registry
    # values. The existing artifact collector uses `GetFileStat` action for this
    # which is horrible.
    args = jobs_pb2.GetFileStatRequest()
    args.pathspec.pathtype = jobs_pb2.PathSpec.PathType.REGISTRY
    args.pathspec.path = (
        r"HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\CSAgent\Sim\AG"
    )

    self.CallClientProto(
        server_stubs.GetFileStat,
        args,
        next_state=self._OnWindowsResponse.__name__,
    )

  def _StartRRGMacOS(self) -> None:
    # The agent identifier is stored in the first 16 bytes of the file so we
    # request only as much.
    action = rrg_stubs.GetFileContents()
    action.args.paths.add().raw_bytes = (
        "/Library/Application Support/CrowdStrike/Falcon/registry.base"
    ).encode()
    action.args.offset = 0
    action.args.length = 16
    action.Call(self._OnMacOSRRGResponse)

  def _StartMacOS(self) -> None:
    # The agent identifier is stored in the first 16 bytes of the file so we
    # request only as much.
    args = jobs_pb2.BufferReference()
    args.pathspec.pathtype = jobs_pb2.PathSpec.PathType.OS
    args.pathspec.path = (
        "/Library/Application Support/CrowdStrike/Falcon/registry.base"
    )
    args.offset = 0
    args.length = 16

    self.CallClientProto(
        server_stubs.TransferBuffer,
        args,
        next_state=self._OnMacOSResponse.__name__,
    )

  @flow_base.UseProto2AnyResponses
  def _OnLinuxRRGResponse(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    if not responses.success:
      self.Log("Failed to retrieve agent identifier: %s", responses.status)
      return

    if len(responses) != 1:
      raise flow_base.FlowError(f"Unexpected response count: {len(responses)}")

    response = rrg_execute_signed_command_pb2.Result()
    response.ParseFromString(list(responses)[0].value)

    stdout = response.stdout.decode("utf-8", errors="ignore")
    if (match := _LINUX_AID_REGEX.search(stdout)) is None:
      self.Log("Malformed `falconctl` output: %s", stdout)
      return

    result = crowdstrike_pb2.GetCrowdstrikeAgentIdResult()
    result.agent_id = match.group("aid")
    self.SendReplyProto(result)

  @flow_base.UseProto2AnyResponses
  def _OnLinuxResponse(
      self, responses: flow_responses.Responses[any_pb2.Any]
  ) -> None:
    if not responses.success:
      self.Log("Failed to retrieve agent identifier: %s", responses.status)
      return

    if len(responses) != 1:
      raise flow_base.FlowError(f"Unexpected response count: {len(responses)}")

    response_any = list(responses)[0]
    if not response_any.type_url.endswith(jobs_pb2.ExecuteResponse.__name__):
      raise flow_base.FlowError(
          f"Unexpected response type: {response_any.type_url}"
      )

    response = jobs_pb2.ExecuteResponse()
    response.ParseFromString(response_any.value)

    stdout = response.stdout.decode("utf-8", errors="ignore")
    if (match := _LINUX_AID_REGEX.search(stdout)) is None:
      self.Log("Malformed `falconctl` output: %s", stdout)
      return

    result = crowdstrike_pb2.GetCrowdstrikeAgentIdResult()
    result.agent_id = match.group("aid")
    self.SendReplyProto(result)

  @flow_base.UseProto2AnyResponses
  def _OnWindowsRRGResponse(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    if not responses.success:
      self.Log("Failed to retrieve agent identifier: %s", responses.status)
      return

    if len(responses) != 1:
      raise flow_base.FlowError(f"Unexpected response count: {len(responses)}")

    response = rrg_get_winreg_value_pb2.Result()
    response.ParseFromString(list(responses)[0].value)

    agent_id_bytes = response.value.bytes

    result = crowdstrike_pb2.GetCrowdstrikeAgentIdResult()
    result.agent_id = binascii.hexlify(agent_id_bytes).decode("ascii")
    self.SendReplyProto(result)

  @flow_base.UseProto2AnyResponses
  def _OnWindowsResponse(
      self, responses: flow_responses.Responses[any_pb2.Any]
  ) -> None:
    if not responses.success:
      self.Log("Failed to retrieve agent identifier: %s", responses.status)
      return

    if len(responses) != 1:
      raise flow_base.FlowError(f"Unexpected response count: {len(responses)}")

    response_any = list(responses)[0]
    if not response_any.type_url.endswith(jobs_pb2.StatEntry.__name__):
      raise flow_base.FlowError(
          f"Unexpected response type: {response_any.type_url}"
      )

    response = jobs_pb2.StatEntry()
    response.ParseFromString(response_any.value)

    agent_id_bytes = response.registry_data.data

    result = crowdstrike_pb2.GetCrowdstrikeAgentIdResult()
    result.agent_id = binascii.hexlify(agent_id_bytes).decode("ascii")
    self.SendReplyProto(result)

  @flow_base.UseProto2AnyResponses
  def _OnMacOSRRGResponse(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    if not responses.success:
      self.Log("Failed to retrieve agent identifier: %s", responses.status)
      return

    if len(responses) != 1:
      raise flow_base.FlowError(f"Unexpected response count: {len(responses)}")

    response = rrg_get_file_contents_pb2.Result()
    response.ParseFromString(list(responses)[0].value)

    if response.error:
      self.Log(f"Failed to get file contents: {response.error}")
      return

    blob_id = models_blobs.BlobID(response.blob_sha256)
    blob = data_store.BLOBS.ReadAndWaitForBlob(blob_id, _BLOB_WAIT_TIMEOUT)
    if blob is None:
      raise flow_base.FlowError(f"Blob {blob_id!r} not found")

    result = crowdstrike_pb2.GetCrowdstrikeAgentIdResult()
    result.agent_id = binascii.hexlify(blob).decode("ascii")
    self.SendReplyProto(result)

  @flow_base.UseProto2AnyResponses
  def _OnMacOSResponse(
      self, responses: flow_responses.Responses[any_pb2.Any]
  ) -> None:
    assert data_store.BLOBS is not None

    if not responses.success:
      self.Log("Failed to retrieve agent identifier: %s", responses.status)
      return

    if len(responses) != 1:
      raise flow_base.FlowError(f"Unexpected response count: {len(responses)}")

    response_any = list(responses)[0]
    if not response_any.type_url.endswith(jobs_pb2.BufferReference.__name__):
      raise flow_base.FlowError(
          f"Unexpected response type: {response_any.type_url}"
      )

    response = jobs_pb2.BufferReference()
    response.ParseFromString(response_any.value)

    blob_id = models_blobs.BlobID(response.data)
    blob = data_store.BLOBS.ReadAndWaitForBlob(blob_id, _BLOB_WAIT_TIMEOUT)
    if blob is None:
      raise flow_base.FlowError(f"Blob {blob_id!r} not found")

    result = crowdstrike_pb2.GetCrowdstrikeAgentIdResult()
    result.agent_id = binascii.hexlify(blob).decode("ascii")
    self.SendReplyProto(result)


_LINUX_AID_REGEX = re.compile(r"aid=\"(?P<aid>[0-9A-Fa-f]+)\"")
_BLOB_WAIT_TIMEOUT = rdfvalue.Duration.From(30, rdfvalue.SECONDS)
