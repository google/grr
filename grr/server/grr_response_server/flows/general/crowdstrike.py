#!/usr/bin/env python
"""Flows related to CrowdStrike security software."""
import binascii
import re

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_action as rdf_client_action
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import crowdstrike_pb2
from grr_response_server import data_store
from grr_response_server import flow_base
from grr_response_server import flow_responses
from grr_response_server import server_stubs
from grr_response_server.models import blobs


class GetCrowdstrikeAgentIdResult(rdf_structs.RDFProtoStruct):
  protobuf = crowdstrike_pb2.GetCrowdstrikeAgentIdResult
  rdf_deps = []


class GetCrowdStrikeAgentID(flow_base.FlowBase):
  """Flow that retrieves the identifier of the CrowdStrike agent."""

  friendly_name = "Get CrowdStrike agent identifier"
  category = "/Collectors/"

  result_types = (GetCrowdstrikeAgentIdResult,)

  def Start(self) -> None:
    if self.client_os == "Linux":
      return self._StartLinux()
    elif self.client_os == "Windows":
      return self._StartWindows()
    elif self.client_os == "Darwin":
      return self._StartMacOS()
    else:
      raise flow_base.FlowError(f"Unexpected system: {self.client_os}")

  def _StartLinux(self) -> None:
    args = rdf_client_action.ExecuteRequest()
    args.cmd = "/opt/CrowdStrike/falconctl"
    args.args = ["-g", "--cid", "--aid"]

    self.CallClient(
        server_stubs.ExecuteCommand,
        args,
        next_state=self._OnLinuxResponse.__name__,
    )

  def _StartWindows(self) -> None:
    # TODO: There is no dedicated action for obtaining registry
    # values. The existing artifact collector uses `GetFileStat` action for this
    # which is horrible.
    args = rdf_client_action.GetFileStatRequest()
    args.pathspec.pathtype = rdf_paths.PathSpec.PathType.REGISTRY
    args.pathspec.path = (
        r"HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\CSAgent\Sim\AG"
    )

    self.CallClient(
        server_stubs.GetFileStat,
        args,
        next_state=self._OnWindowsResponse.__name__,
    )

  def _StartMacOS(self) -> None:
    # The agent identifier is stored in the first 16 bytes of the file so we
    # request only as much.
    args = rdf_client.BufferReference()
    args.pathspec.pathtype = rdf_paths.PathSpec.PathType.OS
    args.pathspec.path = (
        "/Library/Application Support/CrowdStrike/Falcon/registry.base"
    )
    args.offset = 0
    args.length = 16

    self.CallClient(
        server_stubs.TransferBuffer,
        args,
        next_state=self._OnMacOSResponse.__name__,
    )

  def _OnLinuxResponse(self, responses: flow_responses.Responses) -> None:
    if not responses.success:
      self.Log("Failed to retrieve agent identifier: %s", responses.status)
      return

    if len(responses) != 1:
      raise flow_base.FlowError(f"Unexpected response count: {len(responses)}")

    response = responses.First()
    if not isinstance(response, rdf_client_action.ExecuteResponse):
      raise flow_base.FlowError(f"Unexpected response type: {type(response)!r}")

    stdout = response.stdout.decode("utf-8", errors="ignore")
    if (match := _LINUX_AID_REGEX.search(stdout)) is None:
      self.Log("Malformed `falconctl` output: %s", stdout)
      return

    result = GetCrowdstrikeAgentIdResult()
    result.agent_id = match.group("aid")
    self.SendReply(result)

  def _OnWindowsResponse(self, responses: flow_responses.Responses) -> None:
    if not responses.success:
      self.Log("Failed to retrieve agent identifier: %s", responses.status)
      return

    if len(responses) != 1:
      raise flow_base.FlowError(f"Unexpected response count: {len(responses)}")

    response = responses.First()
    if not isinstance(response, rdf_client_fs.StatEntry):
      raise flow_base.FlowError(f"Unexpected response type: {type(response)!r}")

    agent_id_bytes = response.registry_data.data

    result = GetCrowdstrikeAgentIdResult()
    result.agent_id = binascii.hexlify(agent_id_bytes).decode("ascii")
    self.SendReply(result)

  def _OnMacOSResponse(self, responses: flow_responses.Responses) -> None:
    assert data_store.BLOBS is not None

    if not responses.success:
      self.Log("Failed to retrieve agent identifier: %s", responses.status)
      return

    if len(responses) != 1:
      raise flow_base.FlowError(f"Unexpected response count: {len(responses)}")

    response = responses.First()
    if not isinstance(response, rdf_client.BufferReference):
      raise flow_base.FlowError(f"Unexpected response type: {type(response)!r}")

    blob_id = blobs.BlobID(response.data)
    blob = data_store.BLOBS.ReadAndWaitForBlob(blob_id, _BLOB_WAIT_TIMEOUT)
    if blob is None:
      raise flow_base.FlowError(f"Blob {blob_id!r} not found")

    result = GetCrowdstrikeAgentIdResult()
    result.agent_id = binascii.hexlify(blob).decode("ascii")
    self.SendReply(result)


_LINUX_AID_REGEX = re.compile(r"aid=\"(?P<aid>[0-9A-Fa-f]+)\"")
_BLOB_WAIT_TIMEOUT = rdfvalue.Duration.From(30, rdfvalue.SECONDS)
