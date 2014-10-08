#!/usr/bin/env python
"""Simple parsers for the output of WMI queries."""

import binascii
import calendar


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
                         "WMIAccountUsersDomain",
                         "WMIUsers"]

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


class WMIInterfacesParser(parsers.WMIQueryParser):
  """Parser for WMI output. Yields SoftwarePackage rdfvalues."""

  output_types = ["Interface", "DNSClientConfiguration"]
  supported_artifacts = []

  def WMITimeStrToRDFDatetime(self, timestr):
    """Return RDFDatetime from string like 20140825162259.000000-420.

    Args:
      timestr: WMI time string
    Returns:
      rdfvalue.RDFDatetime

    We have some timezone manipulation work to do here because the UTC offset is
    in minutes rather than +-HHMM
    """
    # We use manual parsing here because the time functions provided (datetime,
    # dateutil) do not properly deal with timezone information.
    offset_minutes = timestr[21:]
    year = timestr[:4]
    month = timestr[4:6]
    day = timestr[6:8]
    hours = timestr[8:10]
    minutes = timestr[10:12]
    seconds = timestr[12:14]
    microseconds = timestr[15:21]

    unix_seconds = calendar.timegm(
        map(int, [year, month, day, hours, minutes, seconds]))
    unix_seconds -= int(offset_minutes) * 60
    return rdfvalue.RDFDatetime(unix_seconds * 1e6 + int(microseconds))

  def _ConvertIPs(self, io_tuples, interface, output_dict):
    for inputkey, outputkey in io_tuples:
      addresses = []
      if isinstance(interface[inputkey], list):
        for ip_address in interface[inputkey]:
          addresses.append(rdfvalue.NetworkAddress(
              human_readable_address=ip_address))
      else:
        addresses.append(rdfvalue.NetworkAddress(
            human_readable_address=interface[inputkey]))
      output_dict[outputkey] = addresses
    return output_dict

  def Parse(self, query, result, knowledge_base):
    """Parse the wmi packages output."""
    _ = query, knowledge_base

    args = {"ifname": result["Description"]}
    args["mac_address"] = binascii.unhexlify(
        result["MACAddress"].replace(":", ""))

    self._ConvertIPs([("IPAddress", "addresses"),
                      ("DefaultIPGateway", "ip_gateway_list"),
                      ("DHCPServer", "dhcp_server_list")], result, args)

    if "DHCPLeaseExpires" in result:
      args["dhcp_lease_expires"] = self.WMITimeStrToRDFDatetime(
          result["DHCPLeaseExpires"])

    if "DHCPLeaseObtained" in result:
      args["dhcp_lease_obtained"] = self.WMITimeStrToRDFDatetime(
          result["DHCPLeaseObtained"])

    yield rdfvalue.Interface(**args)

    yield rdfvalue.DNSClientConfiguration(
        dns_server=result["DNSServerSearchOrder"],
        dns_suffix=result["DNSDomainSuffixSearchOrder"])
