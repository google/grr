#!/usr/bin/env python
"""Simple parsers for the output of WMI queries."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import binascii
import calendar
import struct
import time

from future.builtins import bytes
from future.builtins import map
from future.builtins import range
from future.builtins import str
from future.utils import iteritems

from grr_response_core.lib import parser
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import anomaly as rdf_anomaly
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import client_network as rdf_client_network
from grr_response_core.lib.rdfvalues import wmi as rdf_wmi
from grr_response_core.lib.util import compatibility
from grr_response_core.lib.util import precondition


def BinarySIDtoStringSID(sid):
  """Converts a binary SID to its string representation.

  https://msdn.microsoft.com/en-us/library/windows/desktop/aa379597.aspx

  The byte representation of an SID is as follows:
    Offset  Length  Description
    00      01      revision
    01      01      sub-authority count
    02      06      authority (big endian)
    08      04      subauthority #1 (little endian)
    0b      04      subauthority #2 (little endian)
    ...

  Args:
    sid: A `bytes` instance for a SID to convert.

  Returns:
    A `unicode` representation of given SID.

  Raises:
    ValueError: If the binary SID is malformed.
  """
  precondition.AssertType(sid, bytes)

  # TODO: This seemingly no-op is actually not a no-op. The reason
  # is that `sid` might be either `bytes` from the future package or `str` (e.g.
  # a bytes literal on Python 2). This call ensures that we get a `bytes` object
  # with Python 3 semantics. Once GRR's codebase is ready to drop support for
  # Python 2 this line can be removed as indeed then it would be a no-op.
  sid = bytes(sid)

  if not sid:
    return u""

  str_sid_components = [sid[0]]
  # Now decode the 48-byte portion

  if len(sid) >= 8:
    subauthority_count = sid[1]

    identifier_authority = struct.unpack(">H", sid[2:4])[0]
    identifier_authority <<= 32
    identifier_authority |= struct.unpack(">L", sid[4:8])[0]
    str_sid_components.append(identifier_authority)

    start = 8
    for i in range(subauthority_count):
      authority = sid[start:start + 4]
      if not authority:
        break

      if len(authority) < 4:
        message = ("In binary SID '%s', component %d has been truncated. "
                   "Expected 4 bytes, found %d: (%s)")
        message %= (sid, i, len(authority), authority)
        raise ValueError(message)

      str_sid_components.append(struct.unpack("<L", authority)[0])
      start += 4

  return u"S-%s" % (u"-".join(map(str, str_sid_components)))


class WMIEventConsumerParser(parser.WMIQueryParser):
  """Base class for WMI EventConsumer Parsers."""

  __abstract = True  # pylint: disable=invalid-name

  def ParseMultiple(self, result_dicts):
    """Parse WMI Event Consumers."""
    for result_dict in result_dicts:
      wmi_dict = result_dict.ToDict()

      try:
        creator_sid_bytes = bytes(wmi_dict["CreatorSID"])
        wmi_dict["CreatorSID"] = BinarySIDtoStringSID(creator_sid_bytes)
      except ValueError:
        # We recover from corrupt SIDs by outputting it raw as a string
        wmi_dict["CreatorSID"] = compatibility.Repr(wmi_dict["CreatorSID"])
      except KeyError:
        pass

      for output_type in self.output_types:
        anomalies = []

        output = rdfvalue.RDFValue.classes[output_type]()
        for k, v in iteritems(wmi_dict):
          try:
            output.Set(k, v)
          except AttributeError as e:
            # Skip any attribute we don't know about
            anomalies.append("Unknown field %s, with value %s" % (k, v))
          except ValueError as e:
            anomalies.append("Invalid value %s for field %s: %s" % (v, k, e))

        # Yield anomalies first to help with debugging
        if anomalies:
          yield rdf_anomaly.Anomaly(
              type="PARSER_ANOMALY",
              generated_by=self.__class__.__name__,
              finding=anomalies)

        # Raise if the parser generated no output but there were fields.
        if wmi_dict and not output:
          raise ValueError("Non-empty dict %s returned empty output." %
                           wmi_dict)

        yield output


class WMIActiveScriptEventConsumerParser(WMIEventConsumerParser):
  """Parser for WMI ActiveScriptEventConsumers.

  https://msdn.microsoft.com/en-us/library/aa384749(v=vs.85).aspx
  """

  output_types = [rdf_wmi.WMIActiveScriptEventConsumer.__name__]
  supported_artifacts = ["WMIEnumerateASEC"]


class WMICommandLineEventConsumerParser(WMIEventConsumerParser):
  """Parser for WMI CommandLineEventConsumers.

  https://msdn.microsoft.com/en-us/library/aa389231(v=vs.85).aspx
  """

  output_types = [rdf_wmi.WMICommandLineEventConsumer.__name__]
  supported_artifacts = ["WMIEnumerateCLEC"]


class WMIInstalledSoftwareParser(parser.WMIQueryParser):
  """Parser for WMI output. Yields a SoftwarePackages rdfvalue."""

  output_types = [rdf_client.SoftwarePackages.__name__]
  supported_artifacts = ["WMIInstalledSoftware"]

  def ParseMultiple(self, result_dicts):
    """Parse the WMI packages output."""
    status = rdf_client.SoftwarePackage.InstallState.INSTALLED
    packages = []
    for result_dict in result_dicts:
      packages.append(
          rdf_client.SoftwarePackage(
              name=result_dict["Name"],
              description=result_dict["Description"],
              version=result_dict["Version"],
              install_state=status))

    if packages:
      yield rdf_client.SoftwarePackages(packages=packages)


class WMIHotfixesSoftwareParser(parser.WMIQueryParser):
  """Parser for WMI output. Yields SoftwarePackage rdfvalues."""

  output_types = [rdf_client.SoftwarePackages.__name__]
  supported_artifacts = ["WMIHotFixes"]

  def AmericanDateToEpoch(self, date_str):
    """Take a US format date and return epoch."""
    try:
      epoch = time.strptime(date_str, "%m/%d/%Y")
      return int(calendar.timegm(epoch)) * 1000000
    except ValueError:
      return 0

  def ParseMultiple(self, result_dicts):
    """Parse the WMI packages output."""
    status = rdf_client.SoftwarePackage.InstallState.INSTALLED

    packages = []
    for result_dict in result_dicts:
      result = result_dict.ToDict()

      # InstalledOn comes back in a godawful format such as '7/10/2013'.
      installed_on = self.AmericanDateToEpoch(result.get("InstalledOn", ""))
      packages.append(
          rdf_client.SoftwarePackage(
              name=result.get("HotFixID"),
              description=result.get("Caption"),
              installed_by=result.get("InstalledBy"),
              install_state=status,
              installed_on=installed_on))

    if packages:
      yield rdf_client.SoftwarePackages(packages=packages)


class WMIUserParser(parser.WMIQueryParser):
  """Parser for WMI Win32_UserAccount and Win32_UserProfile output."""

  output_types = [rdf_client.User.__name__]
  supported_artifacts = [
      "WMIProfileUsersHomeDir", "WMIAccountUsersDomain", "WMIUsers"
  ]

  account_mapping = {
      # Win32_UserAccount
      "Name": "username",
      "Domain": "userdomain",
      "SID": "sid",
      # Win32_UserProfile
      "LocalPath": "homedir"
  }

  def ParseMultiple(self, result_dicts):
    """Parse the WMI Win32_UserAccount output."""
    for result_dict in result_dicts:
      kb_user = rdf_client.User()
      for wmi_key, kb_key in iteritems(self.account_mapping):
        try:
          kb_user.Set(kb_key, result_dict[wmi_key])
        except KeyError:
          pass
      # We need at least a sid or a username.  If these are missing its likely
      # we retrieved just the userdomain for an AD account that has a name
      # collision with a local account that is correctly populated.  We drop the
      # bogus domain account.
      if kb_user.sid or kb_user.username:
        yield kb_user


class WMILogicalDisksParser(parser.WMIQueryParser):
  """Parser for LogicalDisk WMI output. Yields Volume rdfvalues."""

  output_types = [rdf_client_fs.Volume.__name__]
  supported_artifacts = ["WMILogicalDisks"]

  def ParseMultiple(self, result_dicts):
    """Parse the WMI packages output."""
    for result_dict in result_dicts:
      result = result_dict.ToDict()
      winvolume = rdf_client_fs.WindowsVolume(
          drive_letter=result.get("DeviceID"),
          drive_type=result.get("DriveType"))

      try:
        size = int(result.get("Size"))
      except (ValueError, TypeError):
        size = None

      try:
        free_space = int(result.get("FreeSpace"))
      except (ValueError, TypeError):
        free_space = None

      # Since we don't get the sector sizes from WMI, we just set them at 1 byte
      yield rdf_client_fs.Volume(
          windowsvolume=winvolume,
          name=result.get("VolumeName"),
          file_system_type=result.get("FileSystem"),
          serial_number=result.get("VolumeSerialNumber"),
          sectors_per_allocation_unit=1,
          bytes_per_sector=1,
          total_allocation_units=size,
          actual_available_allocation_units=free_space)


class WMIComputerSystemProductParser(parser.WMIQueryParser):
  """Parser for WMI Output. Yeilds Identifying Number."""

  output_types = [rdf_client.HardwareInfo.__name__]
  supported_artifacts = ["WMIComputerSystemProduct"]

  def ParseMultiple(self, result_dicts):
    """Parse the WMI output to get Identifying Number."""
    for result_dict in result_dicts:
      # Currently we are only grabbing the Identifying Number
      # as the serial number (catches the unique number for VMs).
      # This could be changed to include more information from
      # Win32_ComputerSystemProduct.

      yield rdf_client.HardwareInfo(
          serial_number=result_dict["IdentifyingNumber"],
          system_manufacturer=result_dict["Vendor"])


class WMIInterfacesParser(parser.WMIQueryParser):
  """Parser for WMI output. Yields SoftwarePackage rdfvalues."""

  output_types = [
      rdf_client_network.Interface.__name__,
      rdf_client_network.DNSClientConfiguration.__name__
  ]
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
        tuple(map(int, [year, month, day, hours, minutes, seconds])))
    unix_seconds -= int(offset_minutes) * 60
    return rdfvalue.RDFDatetime(unix_seconds * 1e6 + int(microseconds))

  def _ConvertIPs(self, io_tuples, interface, output_dict):
    for inputkey, outputkey in io_tuples:
      addresses = []
      if isinstance(interface[inputkey], list):
        for ip_address in interface[inputkey]:
          addresses.append(
              rdf_client_network.NetworkAddress(
                  human_readable_address=ip_address))
      else:
        addresses.append(
            rdf_client_network.NetworkAddress(
                human_readable_address=interface[inputkey]))
      output_dict[outputkey] = addresses
    return output_dict

  def ParseMultiple(self, result_dicts):
    """Parse the WMI packages output."""
    for result_dict in result_dicts:
      args = {"ifname": result_dict["Description"]}
      args["mac_address"] = binascii.unhexlify(
          result_dict["MACAddress"].replace(":", ""))

      self._ConvertIPs([("IPAddress", "addresses"),
                        ("DefaultIPGateway", "ip_gateway_list"),
                        ("DHCPServer", "dhcp_server_list")], result_dict, args)

      if "DHCPLeaseExpires" in result_dict:
        args["dhcp_lease_expires"] = self.WMITimeStrToRDFDatetime(
            result_dict["DHCPLeaseExpires"])

      if "DHCPLeaseObtained" in result_dict:
        args["dhcp_lease_obtained"] = self.WMITimeStrToRDFDatetime(
            result_dict["DHCPLeaseObtained"])

      yield rdf_client_network.Interface(**args)

      yield rdf_client_network.DNSClientConfiguration(
          dns_server=result_dict["DNSServerSearchOrder"],
          dns_suffix=result_dict["DNSDomainSuffixSearchOrder"])
