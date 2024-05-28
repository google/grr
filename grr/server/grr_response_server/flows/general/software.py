#!/usr/bin/env python
"""Flows for collection information about installed software."""
import datetime
import plistlib
import re

from grr_response_core.lib.rdfvalues import client_action as rdf_client_action
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import mig_client
from grr_response_core.lib.rdfvalues import mig_file_finder
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_proto import sysinfo_pb2
from grr_response_server import data_store
from grr_response_server import file_store
from grr_response_server import flow_base
from grr_response_server import flow_responses
from grr_response_server import server_stubs
from grr_response_server.models import blobs


class CollectInstalledSoftware(flow_base.FlowBase):
  """Flow that collects information about software installed on an endpoint."""

  category = "/Collectors/"
  behaviours = flow_base.BEHAVIOUR_DEBUG

  # TODO: Add `result_types` declaration once we migrate away from
  # the artifact collector in this flow and the types are known.

  def Start(self) -> None:
    if self.client_os == "Linux":
      dpkg_args = rdf_client_action.ExecuteRequest()
      dpkg_args.cmd = "/usr/bin/dpkg"
      dpkg_args.args.append("--list")

      self.CallClient(
          server_stubs.ExecuteCommand,
          dpkg_args,
          next_state=self._ProcessDpkgResults.__name__,
      )

      rpm_args = rdf_client_action.ExecuteRequest()
      rpm_args.cmd = "/bin/rpm"

      # TODO: Remove branching once updated agent is rolled out to
      # a reasonable portion of the fleet.
      if self.client_version <= 3473:
        rpm_args.args.append("-qa")
      else:
        rpm_args.args.append("--query")
        rpm_args.args.append("--all")
        rpm_args.args.append("--queryformat")
        # pylint: disable=line-too-long
        # pyformat: disable
        rpm_args.args.append("%{NAME}|%{EPOCH}|%{VERSION}|%{RELEASE}|%{ARCH}|%{INSTALLTIME}|%{VENDOR}|%{SOURCERPM}\n")
        # pylint: enable=line-too-long
        # pyformat: enable

      self.CallClient(
          server_stubs.ExecuteCommand,
          rpm_args,
          next_state=self._ProcessRpmResults.__name__,
      )

    if self.client_os == "Windows":
      win32_product_args = rdf_client_action.WMIRequest()
      win32_product_args.query = """
      SELECT Name, Vendor, Description, InstallDate, InstallDate2, Version
        FROM Win32_Product
      """.strip()

      self.CallClient(
          server_stubs.WmiQuery,
          win32_product_args,
          next_state=self._ProcessWin32ProductResults.__name__,
      )

      win32_quick_fix_engineering_args = rdf_client_action.WMIRequest()
      # TODO: Query only columns that we explicitly care about.
      #
      # So far the artifact used wildcard and so for the time being we simply
      # follow it but we should have explicit list of columns that we care about
      # here instead.
      win32_quick_fix_engineering_args.query = """
      SELECT *
        FROM Win32_QuickFixEngineering
      """.strip()

      self.CallClient(
          server_stubs.WmiQuery,
          win32_quick_fix_engineering_args,
          next_state=self._ProcessWin32QuickFixEngineeringResults.__name__,
      )

    if self.client_os == "Darwin":
      ff_args = flows_pb2.FileFinderArgs()
      ff_args.pathtype = jobs_pb2.PathSpec.PathType.OS
      ff_args.paths.append("/Library/Receipts/InstallHistory.plist")
      ff_args.action.action_type = flows_pb2.FileFinderAction.Action.DOWNLOAD

      self.CallClient(
          server_stubs.FileFinderOS,
          mig_file_finder.ToRDFFileFinderArgs(ff_args),
          next_state=self._ProcessInstallHistoryPlist.__name__,
      )

  def _ProcessDpkgResults(
      self,
      responses: flow_responses.Responses[rdf_client_action.ExecuteResponse],
  ) -> None:
    if not responses.success:
      self.Log("Failed to collect Debian package list: %s", responses.status)
      return

    result = sysinfo_pb2.SoftwarePackages()

    if len(responses) != 1:
      raise flow_base.FlowError(
          f"Unexpected number of responses: {len(responses)}",
      )

    response = list(responses)[0]

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
      self.SendReply(mig_client.ToRDFSoftwarePackages(result))

  def _ProcessRpmResults(
      self,
      responses: flow_responses.Responses[rdf_client_action.ExecuteResponse],
  ) -> None:
    if not responses.success:
      self.Log("Failed to collect RPM package list: %s", responses.status)
      return

    result = sysinfo_pb2.SoftwarePackages()

    if len(responses) != 1:
      raise flow_base.FlowError(
          f"Unexpected number of responses: {len(responses)}",
      )

    response = list(responses)[0]

    if response.exit_status != 0:
      self.Log(
          "RPM quit abnormally (status: %s, stdout: %s, stderr: %s)",
          response.exit_status,
          response.stdout,
          response.stderr,
      )
      return

    stdout = response.stdout.decode("utf-8", "backslashreplace")

    for line in stdout.splitlines():
      # Just in case the output contains any trailing newlines or blanks, we
      # strip each line and skip those that are empty.
      line = line.strip()
      if not line:
        continue

      # TODO: Remove branching once updated agent is rolled out to
      # a reasonable portion of the fleet.
      if self.client_version <= 3473:
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

    if result.packages:
      self.SendReply(mig_client.ToRDFSoftwarePackages(result))

  def _ProcessWin32ProductResults(
      self,
      responses: flow_responses.Responses[rdf_protodict.Dict],
  ):
    if not responses.success:
      self.Log("Failed to collect `Win32_Product`: %s", responses.status)
      return

    result = sysinfo_pb2.SoftwarePackages()

    for response in responses:
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
      self.SendReply(mig_client.ToRDFSoftwarePackages(result))

  def _ProcessWin32QuickFixEngineeringResults(
      self,
      responses: flow_responses.Responses[rdf_protodict.Dict],
  ):
    if not responses.success:
      status = responses.status
      self.Log("Failed to collect `Win32_QuickFixEngineering`: %s", status)
      return

    result = sysinfo_pb2.SoftwarePackages()

    for response in responses:
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
      self.SendReply(mig_client.ToRDFSoftwarePackages(result))

  def _ProcessInstallHistoryPlist(
      self,
      responses: flow_responses.Responses[rdf_file_finder.FileFinderResult],
  ) -> None:
    if not responses.success:
      message = f"Failed to collect install history plist: {responses.status}"
      raise flow_base.FlowError(message)

    if len(responses) != 1:
      message = f"Unexpected number of flow responses: {len(responses)}"
      raise flow_base.FlowError(message)

    response = mig_file_finder.ToProtoFileFinderResult(list(responses)[0])

    blob_ids = [
        blobs.BlobID(chunk.digest) for chunk in response.transferred_file.chunks
    ]
    blobs_by_id = data_store.BLOBS.ReadAndWaitForBlobs(
        blob_ids,
        timeout=file_store.BLOBS_READ_TIMEOUT,
    )

    content = b"".join(blobs_by_id[blob_id] for blob_id in blob_ids)
    try:
      plist = plistlib.loads(content, fmt=plistlib.FMT_XML)  # pytype: disable=wrong-arg-types
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

    if result.packages:
      self.SendReply(mig_client.ToRDFSoftwarePackages(result))


_RPM_PACKAGE_REGEX = re.compile(
    r"^(?P<name>.*)-(?P<version>.*-\d+\.\w+)\.(?P<arch>\w+)$"
)
