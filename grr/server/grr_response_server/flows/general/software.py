#!/usr/bin/env python
"""Flows for collection information about installed software."""

import datetime
import itertools
import plistlib
import re

from google.protobuf import any_pb2
from grr_response_core.lib.rdfvalues import mig_protodict
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_proto import signed_commands_pb2
from grr_response_proto import sysinfo_pb2
from grr_response_server import data_store
from grr_response_server import file_store
from grr_response_server import flow_base
from grr_response_server import flow_responses
from grr_response_server import rrg_stubs
from grr_response_server import server_stubs
from grr_response_server.models import blobs as models_blobs
from grr_response_proto.rrg import os_pb2 as rrg_os_pb2
from grr_response_proto.rrg.action import execute_signed_command_pb2 as rrg_execute_signed_command_pb2
from grr_response_proto.rrg.action import get_file_contents_pb2 as rrg_get_file_contents_pb2
from grr_response_proto.rrg.action import query_wmi_pb2 as rrg_query_wmi_pb2


class CollectInstalledSoftware(flow_base.FlowBase):
  """Flow that collects information about software installed on an endpoint."""

  category = "/Collectors/"
  behaviours = flow_base.BEHAVIOUR_DEBUG
  proto_result_types = (sysinfo_pb2.SoftwarePackages,)

  def Start(self) -> None:
    if self.rrg_version >= (0, 0, 2) and self.rrg_os_type == rrg_os_pb2.LINUX:
      dpkg_query_signed_command = data_store.REL_DB.ReadSignedCommand(
          "dpkg_query_show_showformat",
          operating_system=signed_commands_pb2.SignedCommand.LINUX,
      )

      dpkg_query = rrg_stubs.ExecuteSignedCommand()
      dpkg_query.args.command = dpkg_query_signed_command.command
      dpkg_query.args.command_ed25519_signature = (
          dpkg_query_signed_command.ed25519_signature
      )
      dpkg_query.Call(self._ProcessDpkgQueryRrg)  # pyrefly: ignore[bad-argument-type]

      rpm_query_signed_command = data_store.REL_DB.ReadSignedCommand(
          "rpm_query_all_queryformat",
          operating_system=signed_commands_pb2.SignedCommand.LINUX,
      )

      rpm_query = rrg_stubs.ExecuteSignedCommand()
      rpm_query.args.command = rpm_query_signed_command.command
      rpm_query.args.command_ed25519_signature = (
          rpm_query_signed_command.ed25519_signature
      )
      rpm_query.Call(self._ProcessRpmQueryRrg)  # pyrefly: ignore[bad-argument-type]

      return
    elif self.rrg_support and self.rrg_os_type == rrg_os_pb2.WINDOWS:
      query_wmi_product = rrg_stubs.QueryWmi()
      query_wmi_product.args.namespace = "root\\cimv2"
      query_wmi_product.args.query = """
      SELECT
        Name, Vendor, Description, InstallDate, InstallDate2, Version
      FROM
        Win32_Product
      """.strip()
      query_wmi_product.Call(self._ProcessWin32ProductRrg)  # pyrefly: ignore[bad-argument-type]

      query_wmi_qfe = rrg_stubs.QueryWmi()
      query_wmi_qfe.args.namespace = "root\\cimv2"
      query_wmi_qfe.args.query = """
      SELECT
        HotFixID, InstalledOn, InstalledBy, Caption, Description
      FROM
        Win32_QuickFixEngineering
      """.strip()
      query_wmi_qfe.Call(self._ProcessWin32QfeRrg)  # pyrefly: ignore[bad-argument-type]

      return
    elif self.rrg_version >= (0, 0, 9) and self.rrg_os_type == rrg_os_pb2.MACOS:
      get_file_contents = rrg_stubs.GetFileContents()
      get_file_contents.args.mode = rrg_get_file_contents_pb2.INLINE
      get_file_contents.args.paths.add().raw_bytes = (
          "/Library/Receipts/InstallHistory.plist"
      ).encode("utf-8")
      get_file_contents.Call(self._ProcessInstallHistoryPlistRrg)  # pyrefly: ignore[bad-argument-type]

      return

    if self.client_os == "Linux":
      # TODO - Remove branching once updated agent is rolled out to
      # a reasonable portion of the fleet.
      if self.client_version <= 3478:
        dpkg_args = jobs_pb2.ExecuteRequest()
        dpkg_args.cmd = "/usr/bin/dpkg"
        dpkg_args.args.append("--list")

        self.CallClientProto(
            server_stubs.ExecuteCommand,
            dpkg_args,
            next_state=self._ProcessDpkgResults.__name__,
        )
      else:
        dpkg_query_args = jobs_pb2.ExecuteRequest()
        dpkg_query_args.cmd = "/usr/bin/dpkg-query"
        dpkg_query_args.args.append("--show")
        dpkg_query_args.args.append("--showformat")
        # pylint: disable=line-too-long
        # fmt: off
        dpkg_query_args.args.append("${Package}|${Version}|${Architecture}|${Source}|${binary:Synopsis}\n")
        # pylint: enable=line-too-long
        # fmt: on

        self.CallClientProto(
            server_stubs.ExecuteCommand,
            dpkg_query_args,
            next_state=self._ProcessDpkgQueryResults.__name__,
        )

      rpm_args = jobs_pb2.ExecuteRequest()
      rpm_args.cmd = "/bin/rpm"

      # TODO - Remove branching once updated agent is rolled out to
      # a reasonable portion of the fleet.
      if self.client_version <= 3473:
        rpm_args.args.append("-qa")
      else:
        rpm_args.args.append("--query")
        rpm_args.args.append("--all")
        rpm_args.args.append("--queryformat")
        # pylint: disable=line-too-long
        # fmt: off
        rpm_args.args.append("%{NAME}|%{EPOCH}|%{VERSION}|%{RELEASE}|%{ARCH}|%{INSTALLTIME}|%{VENDOR}|%{SOURCERPM}\n")
        # pylint: enable=line-too-long
        # fmt: on

      self.CallClientProto(
          server_stubs.ExecuteCommand,
          rpm_args,
          next_state=self._ProcessRpmResults.__name__,
      )

    if self.client_os == "Windows":
      win32_product_args = jobs_pb2.WMIRequest()
      win32_product_args.query = """
      SELECT Name, Vendor, Description, InstallDate, InstallDate2, Version
        FROM Win32_Product
      """.strip()

      self.CallClientProto(
          server_stubs.WmiQuery,
          win32_product_args,
          next_state=self._ProcessWin32ProductResults.__name__,
      )

      win32_quick_fix_engineering_args = jobs_pb2.WMIRequest()
      # TODO - Query only columns that we explicitly care about.
      #
      # So far the artifact used wildcard and so for the time being we simply
      # follow it but we should have explicit list of columns that we care about
      # here instead.
      win32_quick_fix_engineering_args.query = """
      SELECT *
        FROM Win32_QuickFixEngineering
      """.strip()

      self.CallClientProto(
          server_stubs.WmiQuery,
          win32_quick_fix_engineering_args,
          next_state=self._ProcessWin32QuickFixEngineeringResults.__name__,
      )

    if self.client_os == "Darwin":
      ff_args = flows_pb2.FileFinderArgs()
      ff_args.pathtype = jobs_pb2.PathSpec.PathType.OS
      ff_args.paths.append("/Library/Receipts/InstallHistory.plist")
      ff_args.action.action_type = flows_pb2.FileFinderAction.Action.DOWNLOAD

      self.CallClientProto(
          server_stubs.FileFinderOS,
          ff_args,
          next_state=self._ProcessInstallHistoryPlist.__name__,
      )

  @flow_base.UseProto2AnyResponses  # pyrefly: ignore[bad-argument-type]
  def _ProcessDpkgQueryRrg(
      self,
      responses_any: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    if not responses_any.success:
      self.Log(
          "Failed to collect Debian package list: %s",
          responses_any.status,
      )
      # Note that unlike the legacy version branch, we do not do a fallback to
      # `dpkg --list`. The query we use should be supported by dpkg 1.19.1+
      # (due to `binary:Synopsis` field introduced only there [1]) that was
      # released in September 2018.
      #
      # However, even in case of older dpkg version, the command will not fail
      # on unknown field and instead output empty string. So, in the worst case
      # we will miss a description which is not the end of the world and the
      # fallback would not kick-in anyway.
      #
      # It also seems to be part of the `dpkg` package [2] which is marked as
      # "essential" [3]. Thus, it is pretty much guaranteed to be available on
      # all Debian-based systems.
      #
      # pylint: disable=line-too-long
      # pyformat: disable
      # [1]: https://tracker.debian.org/news/989886/accepted-dpkg-1191-source-into-unstable/
      # [2]: https://manpages.debian.org/unstable/dpkg/
      # [3]: https://packages.debian.org/sid/dpkg
      # pylint: enable=line-too-long
      # pyformat:enable
      return

    if len(responses_any) != 1:
      raise flow_base.FlowError(
          f"Unexpected number of responses: {len(responses_any)}",
      )

    response = rrg_execute_signed_command_pb2.Result()
    response.ParseFromString(list(responses_any)[0].value)

    if response.exit_code != 0:
      self.Log(
          "dpkg quit abnormally (exit code: %s, stdout: %s, stderr: %s)",
          response.exit_code,
          response.stdout.decode("utf-8", "replace"),
          response.stderr.decode("utf-8", "replace"),
      )
      return

    result = self._ParseDpkgQuery(response.stdout)
    if result.packages:
      self.SendReplyProto(result)

  @flow_base.UseProto2AnyResponses  # pyrefly: ignore[bad-argument-type]
  def _ProcessRpmQueryRrg(
      self,
      responses_any: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    if not responses_any.success:
      self.Log(
          "Failed to collect RPM package list: %s",
          responses_any.status,
      )
      return

    if len(responses_any) != 1:
      raise flow_base.FlowError(
          f"Unexpected number of responses: {len(responses_any)}",
      )

    response = rrg_execute_signed_command_pb2.Result()
    response.ParseFromString(list(responses_any)[0].value)

    if response.exit_code != 0:
      self.Log(
          "RPM quit abnormally (exit code: %s, stdout: %s, stderr: %s)",
          response.exit_code,
          response.stdout.decode("utf-8", "replace"),
          response.stderr.decode("utf-8", "replace"),
      )
      return

    result = self._ParseRpmQuery(response.stdout)
    if result.packages:
      self.SendReplyProto(result)

  @flow_base.UseProto2AnyResponses  # pyrefly: ignore[bad-argument-type]
  def _ProcessDpkgResults(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    if not responses.success:
      self.Log("Failed to collect Debian package list: %s", responses.status)
      return

    if len(responses) != 1:
      raise flow_base.FlowError(
          f"Unexpected number of responses: {len(responses)}",
      )

    response = jobs_pb2.ExecuteResponse()
    response.ParseFromString(list(responses)[0].value)

    result = sysinfo_pb2.SoftwarePackages()

    if response.exit_status != 0:
      self.Log(
          "dpkg quit abnormally (status: %s, stdout: %s, stderr: %s)",
          response.exit_status,
          response.stdout,
          response.stderr,
      )
      return

    stdout = response.stdout.decode("utf-8", "backslashreplace")
    lines = iter(stdout.splitlines())

    # Output starts with column descriptors and the actual list of packages
    # starts after the separator indicated by `+++-`. Thus, we iterate until
    # we hit this header and continue parsing from there.

    for line in lines:
      if line.startswith("+++-"):
        break

    for line in lines:
      # Just in case the output contains any trailing newlines or blanks, we
      # strip each line and skip those that are empty.
      line = line.strip()
      if not line:
        continue

      try:
        [status, name, version, arch, description] = line.split(None, 4)
      except ValueError:
        self.Log("Invalid dpkg package description format: %r", line)
        continue

      package = result.packages.add()
      package.name = name
      package.version = version
      package.architecture = arch
      package.description = description

      # Status indicator is desired state in first char, current state in the
      # second char and error in the third (or empty if installed correctly).
      if status[1:2] == "i":
        package.install_state = sysinfo_pb2.SoftwarePackage.INSTALLED

    if result.packages:
      self.SendReplyProto(result)

  @flow_base.UseProto2AnyResponses  # pyrefly: ignore[bad-argument-type]
  def _ProcessDpkgQueryResults(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:

    def CallDpkgList():
      # Maybe `dpkg-query` is not available or is too old to use the format
      # we specified. We try using `dpkg --list` which is less complete but
      # is more likely to work.
      dpkg_args = jobs_pb2.ExecuteRequest()
      dpkg_args.cmd = "/usr/bin/dpkg"
      dpkg_args.args.append("--list")

      self.CallClientProto(
          server_stubs.ExecuteCommand,
          dpkg_args,
          next_state=self._ProcessDpkgResults.__name__,
      )

    if not responses.success:
      self.Log("Failed to invoke `dpkg-query`: %s", responses.status)
      CallDpkgList()
      return

    if len(responses) != 1:
      raise flow_base.FlowError(
          f"Unexpected number of responses: {len(responses)}",
      )

    response = jobs_pb2.ExecuteResponse()
    response.ParseFromString(list(responses)[0].value)

    if response.exit_status != 0:
      self.Log(
          "`dpkg-query` quit abnormally (status: %s, stdout: %s, stderr: %s)",
          response.exit_status,
          response.stdout,
          response.stderr,
      )
      CallDpkgList()
      return

    result = self._ParseDpkgQuery(response.stdout)
    if result.packages:
      self.SendReplyProto(result)

  def _ParseDpkgQuery(self, stdout: bytes) -> sysinfo_pb2.SoftwarePackages:
    result = sysinfo_pb2.SoftwarePackages()

    for line in stdout.decode("utf-8", "backslashreplace").splitlines():
      # Just in case the output contains any trailing newlines or blanks, we
      # strip each line and skip those that are empty.
      line = line.strip()
      if not line:
        continue

      try:
        [name, version, arch, source_deb, description] = line.split("|", 4)
      except ValueError:
        self.Log("Invalid `dpkg-query` output format: %r", line)
        continue

      package = result.packages.add()
      package.name = name
      package.version = version
      package.architecture = arch
      package.source_deb = source_deb
      package.description = description

    return result

  @flow_base.UseProto2AnyResponses  # pyrefly: ignore[bad-argument-type]
  def _ProcessRpmResults(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    if not responses.success:
      self.Log("Failed to collect RPM package list: %s", responses.status)
      return

    if len(responses) != 1:
      raise flow_base.FlowError(
          f"Unexpected number of responses: {len(responses)}",
      )

    response = jobs_pb2.ExecuteResponse()
    response.ParseFromString(list(responses)[0].value)

    if response.exit_status != 0:
      self.Log(
          "RPM quit abnormally (status: %s, stdout: %s, stderr: %s)",
          response.exit_status,
          response.stdout,
          response.stderr,
      )
      return

    result = self._ParseRpmQuery(response.stdout)
    if result.packages:
      self.SendReplyProto(result)

  def _ParseRpmQuery(self, stdout: bytes) -> sysinfo_pb2.SoftwarePackages:
    result = sysinfo_pb2.SoftwarePackages()

    for line in stdout.decode("utf-8", "backslashreplace").splitlines():
      # Just in case the output contains any trailing newlines or blanks, we
      # strip each line and skip those that are empty.
      line = line.strip()
      if not line:
        continue

      # TODO - Remove branching once updated agent is rolled out to
      # a reasonable portion of the fleet.
      if self.rrg_version < (0, 0, 2) and self.client_version <= 3473:
        if (match := _RPM_PACKAGE_REGEX.match(line)) is None:
          self.Log("Invalid RPM package description format: %r", line)
          continue

        package = result.packages.add()
        package.install_state = sysinfo_pb2.SoftwarePackage.INSTALLED
        package.name = match["name"]
        package.version = match["version"]
        package.architecture = match["arch"]
      else:
        try:
          [
              name,
              epoch,
              version,
              release,
              arch,
              install_time,
              vendor,
              source_rpm,
          ] = line.split("|")
        except ValueError:
          self.Log("Invalid RPM package description format: %r", line)
          continue

        try:
          install_date = datetime.datetime.fromtimestamp(int(install_time))
        except ValueError:
          self.Log("Invalid RPM package installation time: %s", install_time)
          continue

        package = result.packages.add()
        package.install_state = sysinfo_pb2.SoftwarePackage.INSTALLED
        package.name = name
        package.version = f"{version}-{release}"
        package.installed_on = int(install_date.timestamp())

        if arch != "(none)":
          package.architecture = arch

        if epoch != "(none)":
          try:
            package.epoch = int(epoch)
          except ValueError:
            self.Log("Invalid RPM package epoch: %s", epoch)

        if vendor != "(none)":
          package.publisher = vendor

        if source_rpm != "(none)":
          package.source_rpm = source_rpm

    return result

  @flow_base.UseProto2AnyResponses  # pyrefly: ignore[bad-argument-type]
  def _ProcessWin32ProductRrg(
      self,
      responses_any: flow_responses.Responses[any_pb2.Any],
  ):
    if not responses_any.success:
      self.Log(
          "Failed to collect `Win32_Product`: %s",
          responses_any.status,
      )
      return

    result = sysinfo_pb2.SoftwarePackages()

    for response_any in responses_any:
      response = rrg_query_wmi_pb2.Result()
      response.ParseFromString(response_any.value)

      package = result.packages.add()
      package.install_state = sysinfo_pb2.SoftwarePackage.INSTALLED

      if name := response.row["Name"].string:
        package.name = name

      if description := response.row["Description"].string:
        package.description = description

      if version := response.row["Version"].string:
        package.version = version

      if vendor := response.row["Vendor"].string:
        package.publisher = vendor

      if install_date := response.row["InstallDate"].string:
        try:
          install_date = datetime.datetime.strptime(install_date, "%Y%m%d")
          package.installed_on = int(install_date.timestamp() * 1_000_000)
        except ValueError:
          self.Log("Invalid product installation date: %s", install_date)

    if result.packages:
      self.SendReplyProto(result)

  @flow_base.UseProto2AnyResponses  # pyrefly: ignore[bad-argument-type]
  def _ProcessWin32QfeRrg(
      self,
      responses_any: flow_responses.Responses[any_pb2.Any],
  ):
    if not responses_any.success:
      self.Log(
          "Failed to collect `Win32_QuickFixEngineering`: %s",
          responses_any.status,
      )
      return

    result = sysinfo_pb2.SoftwarePackages()

    for response_any in responses_any:
      response = rrg_query_wmi_pb2.Result()
      response.ParseFromString(response_any.value)

      package = result.packages.add()
      package.install_state = sysinfo_pb2.SoftwarePackage.INSTALLED

      if hot_fix_id := response.row["HotFixID"].string:
        package.name = hot_fix_id

      if caption := response.row["Caption"].string:
        package.description = caption

      if description := response.row["Description"].string:
        # We use both WMI "description" and "caption" as source for the output
        # description. If both of them are available, we concatenate the two.
        if package.description:
          package.description = f"{package.description}\n\n{description}"
        else:
          package.description = description

      if installed_by := response.row["InstalledBy"].string:
        package.installed_by = installed_by

      if installed_on := response.row["InstalledOn"].string:
        try:
          install_date = datetime.datetime.strptime(installed_on, "%m/%d/%Y")
          package.installed_on = int(install_date.timestamp() * 1_000_000)
        except ValueError:
          self.Log("Invalid hotfix installation date: %s", installed_on)

    if result.packages:
      self.SendReplyProto(result)

  @flow_base.UseProto2AnyResponses  # pyrefly: ignore[bad-argument-type]
  def _ProcessWin32ProductResults(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ):
    if not responses.success:
      self.Log("Failed to collect `Win32_Product`: %s", responses.status)
      return

    result = sysinfo_pb2.SoftwarePackages()

    for response_any in responses:
      response_proto = jobs_pb2.Dict()
      response_proto.ParseFromString(response_any.value)
      response = mig_protodict.ToRDFDict(response_proto)

      package = result.packages.add()
      package.install_state = sysinfo_pb2.SoftwarePackage.INSTALLED

      if name := response.get("Name"):
        package.name = name

      if description := response.get("Description"):
        package.description = description

      if version := response.get("Version"):
        package.version = version

      if vendor := response.get("Vendor"):
        package.publisher = vendor

      if install_date := response.get("InstallDate"):
        try:
          install_date = datetime.datetime.strptime(install_date, "%Y%m%d")
          package.installed_on = int(install_date.timestamp() * 1_000_000)
        except ValueError:
          self.Log("Invalid product installation date: %s", install_date)

    if result.packages:
      self.SendReplyProto(result)

  @flow_base.UseProto2AnyResponses  # pyrefly: ignore[bad-argument-type]
  def _ProcessWin32QuickFixEngineeringResults(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ):
    if not responses.success:
      status = responses.status
      self.Log("Failed to collect `Win32_QuickFixEngineering`: %s", status)
      return

    result = sysinfo_pb2.SoftwarePackages()

    for response_any in responses:
      response_proto = jobs_pb2.Dict()
      response_proto.ParseFromString(response_any.value)
      response = mig_protodict.ToRDFDict(response_proto)

      package = result.packages.add()

      if hot_fix_id := response.get("HotFixID"):
        package.name = hot_fix_id

      if caption := response.get("Caption"):
        package.description = caption

      if description := response.get("Description"):
        # We use both WMI "description" and "caption" as source for the output
        # description. If both of them are available, we concatenate the two.
        if package.description:
          package.description = f"{package.description}\n\n{description}"
        else:
          package.description = description

      if installed_by := response.get("InstalledBy"):
        package.installed_by = installed_by

      if installed_on := response.get("InstalledOn"):
        try:
          install_date = datetime.datetime.strptime(installed_on, "%m/%d/%Y")
          package.installed_on = int(install_date.timestamp() * 1_000_000)
        except ValueError:
          self.Log("Invalid hotfix installation date: %s", installed_on)

    if result.packages:
      self.SendReplyProto(result)

  @flow_base.UseProto2AnyResponses  # pyrefly: ignore[bad-argument-type]
  def _ProcessInstallHistoryPlistRrg(
      self,
      responses_any: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    if not responses_any.success:
      raise flow_base.FlowError(
          f"Failed to collect install history plist: {responses_any.status}",
      )

    responses = []
    for response_any in responses_any:
      response = rrg_get_file_contents_pb2.Result()
      response.ParseFromString(response_any.value)

      responses.append(response)

    responses = sorted(responses, key=lambda _: _.offset)
    for response_curr, response_next in itertools.pairwise(responses):
      if response_curr.offset + response_curr.length != response_next.offset:
        raise flow_base.FlowError(
            f"Missing response for install history plist file': {responses}",
        )

    content = b"".join(response.blob_contents for response in responses)

    result = self._ParseInstallHistoryPlist(content)
    if result.packages:
      self.SendReplyProto(result)

  @flow_base.UseProto2AnyResponses  # pyrefly: ignore[bad-argument-type]
  def _ProcessInstallHistoryPlist(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    if not responses.success:
      message = f"Failed to collect install history plist: {responses.status}"
      raise flow_base.FlowError(message)

    if len(responses) != 1:
      message = f"Unexpected number of flow responses: {len(responses)}"
      raise flow_base.FlowError(message)

    response = flows_pb2.FileFinderResult()
    response.ParseFromString(list(responses)[0].value)

    blob_ids = [
        models_blobs.BlobID(chunk.digest)
        for chunk in response.transferred_file.chunks
    ]
    blobs_by_id = data_store.BLOBS.ReadAndWaitForBlobs(
        blob_ids,
        timeout=file_store.BLOBS_READ_TIMEOUT,
    )

    content = b"".join(blobs_by_id[blob_id] for blob_id in blob_ids)  # pyrefly: ignore[bad-argument-type]

    result = self._ParseInstallHistoryPlist(content)
    if result.packages:
      self.SendReplyProto(result)

  def _ParseInstallHistoryPlist(
      self,
      content: bytes,
  ) -> sysinfo_pb2.SoftwarePackages:
    try:
      plist = plistlib.loads(content, fmt=plistlib.FMT_XML)
    except plistlib.InvalidFileException as error:
      message = f"Failed to parse install history plist: {error}"
      raise flow_base.FlowError(message) from error

    if not isinstance(plist, list):
      message = f"Unexpected install history plist type: {type(plist)}"
      raise flow_base.FlowError(message)

    result = sysinfo_pb2.SoftwarePackages()

    for item in plist:
      package = result.packages.add()

      if display_name := item.get("displayName"):
        package.name = display_name

      if display_version := item.get("displayVersion"):
        package.version = display_version

      if package_identifiers := item.get("packageIdentifiers"):
        package.description = ",".join(package_identifiers)

      if date := item.get("date"):
        package.installed_on = int(date.timestamp() * 1_000_000)

    return result


_RPM_PACKAGE_REGEX = re.compile(
    r"^(?P<name>.*)-(?P<version>.*-\d+\.\w+)\.(?P<arch>\w+)$"
)
