#!/usr/bin/env python
"""Simple parsers for the output of WMI queries."""

from grr.lib import parsers
from grr.lib import rdfvalue
from grr.lib import time_utils


class WMIInstalledSoftwareParser(parsers.WMIQueryParser):
  """Parser for WMI output. Yields SoftwarePackage rdfvalues."""

  output_types = ["SoftwarePackage"]
  supported_artifacts = ["WMIInstalledSoftware"]

  def Parse(self, query, result, knowledge_base):
    """Parse the wmi packages output."""
    _ = query, knowledge_base
    status = rdfvalue.SoftwarePackage.InstallState.INSTALLED
    soft = rdfvalue.SoftwarePackage(
        name=result["Name"],
        description=result["Description"],
        version=result["Version"],
        install_state=status)

    yield soft


class WMIHotfixesSoftwareParser(parsers.WMIQueryParser):
  """Parser for WMI output. Yields SoftwarePackage rdfvalues."""

  output_types = ["SoftwarePackage"]
  supported_artifacts = ["WMIHotFixes"]

  def Parse(self, query, result, knowledge_base):
    """Parse the wmi packages output."""
    _ = query, knowledge_base
    status = rdfvalue.SoftwarePackage.InstallState.INSTALLED
    result = result.ToDict()

    # InstalledOn comes back in a godawful format such as '7/10/2013'.
    installed_on = time_utils.AmericanDateToEpoch(result.get("InstalledOn", ""))
    soft = rdfvalue.SoftwarePackage(
        name=result.get("HotFixID"),
        description=result.get("Caption"),
        installed_by=result.get("InstalledBy"),
        install_state=status,
        installed_on=installed_on)
    yield soft


class WMIUserParser(parsers.WMIQueryParser):
  """Parser for WMI Win32_UserAccount and Win32_UserProfile output."""

  output_types = ["KnowledgeBaseUser"]
  supported_artifacts = ["WMIProfileUsersHomeDir",
                         "WMIAccountUsersDomain"]

  account_mapping = {
      # Win32_UserAccount
      "Name": "username",
      "Domain": "userdomain",
      "SID": "sid",
      # Win32_UserProfile
      "LocalPath": "homedir"
      }

  def Parse(self, query, result, knowledge_base):
    """Parse the wmi Win32_UserAccount output."""
    _ = query, knowledge_base
    kb_user = rdfvalue.KnowledgeBaseUser()
    for wmi_key, kb_key in self.account_mapping.items():
      try:
        kb_user.Set(kb_key, result[wmi_key])
      except KeyError:
        pass
    # We need at least a sid or a username.  If these are missing its likely we
    # retrieved just the userdomain for an AD account that has a name collision
    # with a local account that is correctly populated.  We drop the bogus
    # domain account.
    if kb_user.sid or kb_user.username:
      yield kb_user


class WMILogicalDisksParser(parsers.WMIQueryParser):
  """Parser for LogicalDisk WMI output. Yields Volume rdfvalues."""

  output_types = ["Volume"]
  supported_artifacts = ["WMILogicalDisks"]

  def Parse(self, query, result, knowledge_base):
    """Parse the wmi packages output."""
    _ = query, knowledge_base
    result = result.ToDict()
    winvolume = rdfvalue.WindowsVolume(drive_letter=result.get("DeviceID"),
                                       drive_type=result.get("DriveType"))

    try:
      size = int(result.get("Size"))
    except ValueError:
      size = None

    try:
      free_space = int(result.get("FreeSpace"))
    except ValueError:
      free_space = None

    # Since we don't get the sector sizes from WMI, we just set them at 1 byte
    volume = rdfvalue.Volume(windows=winvolume,
                             name=result.get("VolumeName"),
                             file_system_type=result.get("FileSystem"),
                             serial_number=result.get("VolumeSerialNumber"),
                             sectors_per_allocation_unit=1,
                             bytes_per_sector=1,
                             total_allocation_units=size,
                             actual_available_allocation_units=free_space)

    yield volume
