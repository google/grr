#!/usr/bin/env python
"""Flows for collecting hardware information."""

import plistlib
import re

from google.protobuf import any_pb2
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_proto import jobs_pb2
from grr_response_proto import signed_commands_pb2
from grr_response_proto import sysinfo_pb2
from grr_response_server import data_store
from grr_response_server import flow_base
from grr_response_server import flow_responses
from grr_response_server import rrg_stubs
from grr_response_server import server_stubs
from grr_response_proto.rrg import os_pb2 as rrg_os_pb2
from grr_response_proto.rrg.action import execute_signed_command_pb2 as rrg_execute_signed_command_pb2
from grr_response_proto.rrg.action import query_wmi_pb2 as rrg_query_wmi_pb2


class CollectHardwareInfo(flow_base.FlowBase):
  """Flow that collects information about the hardware of the endpoint."""

  category = "/Collectors/"
  behaviours = flow_base.BEHAVIOUR_DEBUG

  result_types = [rdf_client.HardwareInfo]
  proto_result_types = [sysinfo_pb2.HardwareInfo]

  only_protos_allowed = True

  def Start(self) -> None:
    if self.rrg_support:
      if self.rrg_os_type == rrg_os_pb2.LINUX:
        signed_command = data_store.REL_DB.ReadSignedCommand(
            "dmidecode_q",
            operating_system=signed_commands_pb2.SignedCommand.OS.LINUX,
        )

        action = rrg_stubs.ExecuteSignedCommand()
        action.args.command = signed_command.command
        action.args.command_ed25519_signature = signed_command.ed25519_signature
        action.args.timeout.seconds = 10
        action.Call(self._ProcessRRGDmidecodeResults)
      elif self.rrg_os_type == rrg_os_pb2.WINDOWS:
        action = rrg_stubs.QueryWmi()
        action.args.query = """
        SELECT *
          FROM Win32_ComputerSystemProduct
        """
        action.Call(self._ProcessRRGComputerSystemProductResults)
      elif self.rrg_os_type == rrg_os_pb2.MACOS:
        signed_command = data_store.REL_DB.ReadSignedCommand(
            "system_profiler_xml_sphardware",
            operating_system=signed_commands_pb2.SignedCommand.OS.MACOS,
        )

        action = rrg_stubs.ExecuteSignedCommand()
        action.args.command = signed_command.command
        action.args.command_ed25519_signature = signed_command.ed25519_signature
        action.args.timeout.seconds = 10
        action.Call(self._ProcessRRGSystemProfilerResults)
      else:
        raise flow_base.FlowError(
            f"Unsupported operating system: {self.rrg_os_type}",
        )
    else:
      if self.client_os == "Linux":
        dmidecode_args = jobs_pb2.ExecuteRequest()
        dmidecode_args.cmd = "/usr/sbin/dmidecode"
        dmidecode_args.args.append("-q")

        self.CallClientProto(
            server_stubs.ExecuteCommand,
            dmidecode_args,
            next_state=self._ProcessDmidecodeResults.__name__,
        )
      elif self.client_os == "Windows":
        win32_computer_system_product_args = jobs_pb2.WMIRequest()
        win32_computer_system_product_args.query = """
        SELECT *
          FROM Win32_ComputerSystemProduct
        """.strip()

        self.CallClientProto(
            server_stubs.WmiQuery,
            win32_computer_system_product_args,
            next_state=self._ProcessWin32ComputerSystemProductResults.__name__,
        )
      elif self.client_os == "Darwin":
        system_profiler_args = jobs_pb2.ExecuteRequest()
        system_profiler_args.cmd = "/usr/sbin/system_profiler"
        system_profiler_args.args.append("-xml")
        system_profiler_args.args.append("SPHardwareDataType")

        self.CallClientProto(
            server_stubs.ExecuteCommand,
            system_profiler_args,
            next_state=self._ProcessSystemProfilerResults.__name__,
        )
      else:
        raise flow_base.FlowError(
            f"Unsupported operating system: {self.client_os}",
        )

  @flow_base.UseProto2AnyResponses
  def _ProcessRRGDmidecodeResults(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    if not responses.success:
      self.Log("Failed to run dmidecode: %s", responses.status)
      return

    if len(responses) != 1:
      raise flow_base.FlowError(
          f"Unexpected number of dmidecode responses: {len(responses)}",
      )

    response = rrg_execute_signed_command_pb2.Result()
    response.ParseFromString(list(responses)[0].value)

    if response.exit_code != 0 or response.exit_signal != 0:
      raise flow_base.FlowError(
          "dmidecode quit abnormally "
          f"(code: {response.exit_code}, signal: {response.exit_signal}, "
          f"stdout: {response.stdout}, stderr: {response.stderr})",
      )

    if response.stdout_truncated:
      self.Log("dmidecode output was truncated, parsing might be incomplete")

    self.SendReplyProto(_ParseDmidecodeStdout(response.stdout))

  @flow_base.UseProto2AnyResponses
  def _ProcessDmidecodeResults(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    if not responses.success:
      self.Log("Failed to run dmidecode: %s", responses.status)
      return

    for response_any in responses:
      response = jobs_pb2.ExecuteResponse()
      response.ParseFromString(response_any.value)

      if response.exit_status != 0:
        raise flow_base.FlowError(
            f"dmidecode quit abnormally (status: {response.exit_status}, "
            f"stdout: {response.stdout}, stderr: {response.stderr})",
        )

      result = _ParseDmidecodeStdout(response.stdout)
      self.SendReplyProto(result)

  @flow_base.UseProto2AnyResponses
  def _ProcessRRGComputerSystemProductResults(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    if not responses.success:
      raise flow_base.FlowError(
          f"Failed to run WMI query: {responses.status}",
      )

    responses = list(responses)
    if len(responses) != 1:
      raise flow_base.FlowError(
          f"Unexpected number of WMI query results: {len(responses)}",
      )

    response = rrg_query_wmi_pb2.Result()
    response.ParseFromString(responses[0].value)

    result = sysinfo_pb2.HardwareInfo()

    if identifying_number := response.row["IdentifyingNumber"].string:
      result.serial_number = identifying_number
    if vendor := response.row["Vendor"].string:
      result.system_manufacturer = vendor

    self.SendReplyProto(result)

  @flow_base.UseProto2AnyResponses
  def _ProcessWin32ComputerSystemProductResults(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    if not responses.success:
      raise flow_base.FlowError(
          f"Failed to run WMI query: {responses.status}",
      )

    responses = list(responses)

    if len(responses) != 1:
      raise flow_base.FlowError(
          f"Unexpected number of WMI query results: {len(responses)}",
      )

    response = jobs_pb2.Dict()
    response.ParseFromString(responses[0].value)

    result = sysinfo_pb2.HardwareInfo()

    for kv in response.dat:
      if kv.k.string == "IdentifyingNumber":
        result.serial_number = kv.v.string
      if kv.k.string == "Vendor":
        result.system_manufacturer = kv.v.string

    self.SendReplyProto(result)

  @flow_base.UseProto2AnyResponses
  def _ProcessRRGSystemProfilerResults(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    if not responses.success:
      raise flow_base.FlowError(
          f"Failed to run system profiler: {responses.status}",
      )

    for response_any in responses:
      response = rrg_execute_signed_command_pb2.Result()
      response.ParseFromString(response_any.value)

      if response.exit_code != 0 or response.exit_signal != 0:
        raise flow_base.FlowError(
            "system profiler quit abnormally "
            f"(code: {response.exit_code}, signal: {response.exit_signal}, "
            f"stdout: {response.stdout}, stderr: {response.stderr})",
        )

      self.SendReplyProto(_ParseSystemProfilerStdout(response.stdout))

  @flow_base.UseProto2AnyResponses
  def _ProcessSystemProfilerResults(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    if not responses.success:
      raise flow_base.FlowError(
          f"Failed to run system profiler: {responses.status}",
      )

    for response_any in responses:
      response = jobs_pb2.ExecuteResponse()
      response.ParseFromString(response_any.value)

      if response.exit_status != 0:
        raise flow_base.FlowError(
            f"system profiler quit abnormally (status: {response.exit_status}, "
            f"stdout: {response.stdout}, stderr: {response.stderr})",
        )

      result = _ParseSystemProfilerStdout(response.stdout)
      self.SendReplyProto(result)


# TODO: Inline back to `_Process*DmidecodeResults` once the non-RRG
# branch has been removed.
def _ParseDmidecodeStdout(stdout: bytes) -> sysinfo_pb2.HardwareInfo:
  """Parses standard output of the `/usr/bin/dmidecode` command."""
  result = sysinfo_pb2.HardwareInfo()

  stdout = stdout.decode("utf-8", "backslashreplace")
  lines = iter(stdout.splitlines())

  for line in lines:
    line = line.strip()

    if line == "System Information":
      for line in lines:
        if not line.strip():
          # Blank line ends system information section.
          break
        elif match := re.fullmatch(r"\s*Serial Number:\s*(.*)", line):
          result.serial_number = match[1]
        elif match := re.fullmatch(r"\s*Manufacturer:\s*(.*)", line):
          result.system_manufacturer = match[1]
        elif match := re.fullmatch(r"\s*Product Name:\s*(.*)", line):
          result.system_product_name = match[1]
        elif match := re.fullmatch(r"\s*UUID:\s*(.*)", line):
          result.system_uuid = match[1]
        elif match := re.fullmatch(r"\s*SKU Number:\s*(.*)", line):
          result.system_sku_number = match[1]
        elif match := re.fullmatch(r"\s*Family:\s*(.*)", line):
          result.system_family = match[1]
        elif match := re.fullmatch(r"\s*Asset Tag:\s*(.*)", line):
          result.system_assettag = match[1]

    elif line == "BIOS Information":
      for line in lines:
        if not line.strip():
          # Blank link ends BIOS information section.
          break
        elif match := re.fullmatch(r"^\s*Vendor:\s*(.*)", line):
          result.bios_vendor = match[1]
        elif match := re.fullmatch(r"^\s*Version:\s*(.*)", line):
          result.bios_version = match[1]
        elif match := re.fullmatch(r"^\s*Release Date:\s*(.*)", line):
          result.bios_release_date = match[1]
        elif match := re.fullmatch(r"^\s*ROM Size:\s*(.*)", line):
          result.bios_rom_size = match[1]
        elif match := re.fullmatch(r"^\s*BIOS Revision:\s*(.*)", line):
          result.bios_revision = match[1]

  return result


# TODO: Inline back to `_Process*SystemProfilerResults` once the
# non-RRG branch has been removed.
def _ParseSystemProfilerStdout(stdout: bytes) -> sysinfo_pb2.HardwareInfo:
  """Parses standard output of the `/usr/sbin/system_profiler` command."""
  try:
    plist = plistlib.loads(stdout)
  except plistlib.InvalidFileException as error:
    raise flow_base.FlowError(
        f"Failed to parse system profiler output: {error}",
    )

  if not isinstance(plist, list):
    raise flow_base.FlowError(
        f"Unexpected type of system profiler output: {type(plist)}",
    )

  if len(plist) != 1:
    raise flow_base.FlowError(
        f"Unexpected length of system profiler output: {len(plist)}",
    )

  if not (items := plist[0].get("_items")):
    raise flow_base.FlowError(
        "`_items` property missing in system profiler output",
    )

  if not isinstance(items, list):
    raise flow_base.FlowError(
        f"Unexpected type of system profiler items: {type(items)}",
    )

  if len(items) != 1:
    raise flow_base.FlowError(
        f"Unexpected number of system profiler items: {len(items)}",
    )

  item = items[0]

  if not isinstance(item, dict):
    raise flow_base.FlowError(
        f"Unexpected type of system profiler item: {type(item)}",
    )

  result = sysinfo_pb2.HardwareInfo()

  if serial_number := item.get("serial_number"):
    result.serial_number = serial_number
  if machine_model := item.get("machine_model"):
    result.system_product_name = machine_model
  if boot_rom_version := item.get("boot_rom_version"):
    result.bios_version = boot_rom_version
  if platform_uuid := item.get("platform_UUID"):
    result.system_uuid = platform_uuid

  return result
