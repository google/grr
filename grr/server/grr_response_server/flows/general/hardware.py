#!/usr/bin/env python
"""Flows for collecting hardware information."""

import plistlib
import re

from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_action as rdf_client_action
from grr_response_core.lib.rdfvalues import mig_client
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_proto import sysinfo_pb2
from grr_response_server import flow_base
from grr_response_server import flow_responses
from grr_response_server import server_stubs


class CollectHardwareInfo(flow_base.FlowBase):
  """Flow that collects information about the hardware of the endpoint."""

  category = "/Collectors/"
  behaviours = flow_base.BEHAVIOUR_DEBUG

  result_types = [rdf_client.HardwareInfo]

  def Start(self) -> None:
    if self.client_os == "Linux":
      dmidecode_args = rdf_client_action.ExecuteRequest()
      dmidecode_args.cmd = "/usr/sbin/dmidecode"
      dmidecode_args.args.append("-q")

      self.CallClient(
          server_stubs.ExecuteCommand,
          dmidecode_args,
          next_state=self._ProcessDmidecodeResults.__name__,
      )
    elif self.client_os == "Windows":
      win32_computer_system_product_args = rdf_client_action.WMIRequest()
      win32_computer_system_product_args.query = """
      SELECT *
        FROM Win32_ComputerSystemProduct
      """.strip()

      self.CallClient(
          server_stubs.WmiQuery,
          win32_computer_system_product_args,
          next_state=self._ProcessWin32ComputerSystemProductResults.__name__,
      )
    elif self.client_os == "Darwin":
      system_profiler_args = rdf_client_action.ExecuteRequest()
      system_profiler_args.cmd = "/usr/sbin/system_profiler"
      system_profiler_args.args.append("-xml")
      system_profiler_args.args.append("SPHardwareDataType")

      self.CallClient(
          server_stubs.ExecuteCommand,
          system_profiler_args,
          next_state=self._ProcessSystemProfilerResults.__name__,
      )
    else:
      message = f"Unsupported operating system: {self.client_os}"
      raise flow_base.FlowError(message)

  def _ProcessDmidecodeResults(
      self,
      responses: flow_responses.Responses[rdf_client_action.ExecuteResponse],
  ) -> None:
    if not responses.success:
      raise flow_base.FlowError(
          f"Failed to run dmidecode: {responses.status}",
      )

    for response in responses:
      if response.exit_status != 0:
        raise flow_base.FlowError(
            f"dmidecode quit abnormally (status: {response.exit_status}, "
            f"stdout: {response.stdout}, stderr: {response.stderr})",
        )

      result = sysinfo_pb2.HardwareInfo()

      stdout = response.stdout.decode("utf-8", "backslashreplace")
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

      self.SendReply(mig_client.ToRDFHardwareInfo(result))

  def _ProcessWin32ComputerSystemProductResults(
      self,
      responses: flow_responses.Responses[rdf_protodict.Dict],
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

    response = responses[0]

    result = sysinfo_pb2.HardwareInfo()

    if identifying_number := response.get("IdentifyingNumber"):
      result.serial_number = identifying_number
    if vendor := response.get("Vendor"):
      result.system_manufacturer = vendor

    self.SendReply(mig_client.ToRDFHardwareInfo(result))

  def _ProcessSystemProfilerResults(
      self,
      responses: flow_responses.Responses[rdf_client_action.ExecuteResponse],
  ) -> None:
    if not responses.success:
      raise flow_base.FlowError(
          f"Failed to run system profiler: {responses.status}",
      )

    for response in responses:
      if response.exit_status != 0:
        raise flow_base.FlowError(
            f"system profiler quit abnormally (status: {response.exit_status}, "
            f"stdout: {response.stdout}, stderr: {response.stderr})",
        )

      try:
        plist = plistlib.loads(response.stdout)
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

      self.SendReply(mig_client.ToRDFHardwareInfo(result))
