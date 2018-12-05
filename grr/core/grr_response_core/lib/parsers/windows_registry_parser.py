#!/usr/bin/env python
"""Simple parsers for registry keys and values."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import logging
import os
import re


from future.utils import iteritems
from future.utils import itervalues

from grr_response_core.lib import artifact_utils
from grr_response_core.lib import parser
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import type_info
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs

SID_RE = re.compile(r"^S-\d-\d+-(\d+-){1,14}\d+$")


class CurrentControlSetKBParser(parser.RegistryValueParser):
  """Parser for CurrentControlSet value."""

  output_types = ["RDFString"]
  # TODO(user): remove CurrentControlSet after artifact cleanup.
  supported_artifacts = [
      "WindowsRegistryCurrentControlSet", "CurrentControlSet"
  ]

  def Parse(self, stat, unused_knowledge_base):
    """Parse the key currentcontrolset output."""
    value = stat.registry_data.GetValue()

    if not str(value).isdigit() or int(value) > 999 or int(value) < 0:
      raise parser.ParseError(
          "Invalid value for CurrentControlSet key %s" % value)
    yield rdfvalue.RDFString(
        "HKEY_LOCAL_MACHINE\\SYSTEM\\ControlSet%03d" % int(value))


class WinEnvironmentParser(parser.RegistryValueParser):
  """Parser for registry retrieved environment variables."""

  output_types = ["RDFString"]
  supported_artifacts = [
      "WindowsEnvironmentVariableAllUsersAppData",
      "WindowsEnvironmentVariablePath",
      "WindowsEnvironmentVariableTemp",
      "WindowsEnvironmentVariableWinDir",
  ]
  # Required for environment variable expansion
  knowledgebase_dependencies = ["environ_systemdrive", "environ_systemroot"]

  def Parse(self, stat, knowledge_base):
    """Expand any variables in the value."""
    value = stat.registry_data.GetValue()
    if not value:
      raise parser.ParseError("Invalid value for key %s" % stat.pathspec.path)
    value = artifact_utils.ExpandWindowsEnvironmentVariables(
        value, knowledge_base)
    if value:
      yield rdfvalue.RDFString(value)


class WinSystemDriveParser(parser.RegistryValueParser):
  """Parser for SystemDrive environment variable."""

  output_types = ["RDFString"]
  supported_artifacts = ["WindowsEnvironmentVariableSystemDrive"]

  def Parse(self, stat, _):
    """Parses a SystemDrive environment variable."""
    if isinstance(stat, rdf_client_fs.StatEntry):
      value = stat.registry_data.GetValue()
    elif isinstance(stat, rdfvalue.RDFString):
      value = stat
    if not value:
      raise parser.ParseError("Invalid value for key %s" % stat.pathspec.path)

    systemdrive = value[0:2]
    if re.match(r"^[A-Za-z]:$", systemdrive):
      yield rdfvalue.RDFString(systemdrive)
    else:
      raise parser.ParseError(
          "Bad drive letter for key %s" % stat.pathspec.path)


class WinSystemRootParser(parser.RegistryValueParser):
  """Parser for SystemRoot environment variables."""

  output_types = ["RDFString"]
  supported_artifacts = ["WindowsEnvironmentVariableSystemRoot"]

  def Parse(self, stat, _):
    value = stat.registry_data.GetValue()
    if value:
      yield rdfvalue.RDFString(value)
    else:
      raise parser.ParseError("Invalid value for key %s" % stat.pathspec.path)


class CodepageParser(parser.RegistryValueParser):
  """Parser for Codepage values."""

  output_types = ["RDFString"]
  supported_artifacts = ["WindowsCodePage"]

  def Parse(self, stat, knowledge_base):
    _ = knowledge_base
    value = stat.registry_data.GetValue()
    yield rdfvalue.RDFString("cp_%s" % value)


class ProfilesDirectoryEnvironmentVariable(parser.RegistryParser):
  """Parser for the ProfilesDirectory environment variable."""

  output_type = ["RDFString"]
  supported_artifacts = ["WindowsEnvironmentVariableProfilesDirectory"]
  knowledgebase_dependencies = ["environ_systemdrive", "environ_systemroot"]

  def Parse(self, stat, knowledge_base):
    value = stat.registry_data.GetValue()
    if not value:
      # Provide a default, if the registry value is not available.
      value = "%SystemDrive%\\Documents and Settings"
    interpolated_value = artifact_utils.ExpandWindowsEnvironmentVariables(
        value, knowledge_base)
    yield rdfvalue.RDFString(interpolated_value)


class AllUsersProfileEnvironmentVariable(parser.RegistryParser):
  """Parser for AllUsersProfile variable."""

  output_types = ["RDFString"]
  supported_artifacts = ["WindowsEnvironmentVariableAllUsersProfile"]
  knowledgebase_dependencies = ["environ_profilesdirectory"]

  def Parse(self, stat, knowledge_base):
    value = stat.registry_data.GetValue() or "All Users"
    all_users_dir = artifact_utils.ExpandWindowsEnvironmentVariables(
        "%ProfilesDirectory%\\" + value, knowledge_base)
    yield rdfvalue.RDFString(all_users_dir)


class WinUserSids(parser.RegistryParser):
  """Parser for extracting SID for multiple users.

  This reads a listing of the profile paths to extract a list of SIDS for
  users with profiles on a system.
  """
  output_types = ["User"]
  supported_artifacts = ["WindowsRegistryProfiles"]

  def Parse(self, stat, knowledge_base):
    """Parse each returned registry value."""
    _ = knowledge_base  # Unused.
    sid_str = stat.pathspec.Dirname().Basename()

    if SID_RE.match(sid_str):
      kb_user = rdf_client.User()
      kb_user.sid = sid_str
      if stat.pathspec.Basename() == "ProfileImagePath":
        if stat.resident:
          # Support old clients.
          kb_user.homedir = utils.SmartUnicode(stat.resident)
        else:
          kb_user.homedir = stat.registry_data.GetValue()

        kb_user.userprofile = kb_user.homedir
        try:
          # Assume username is the last component of the path. This is not
          # robust, but other user artifacts will override it if there is a
          # better match.
          kb_user.username = kb_user.homedir.rsplit("\\", 1)[-1]
        except IndexError:
          pass

      yield kb_user


class WinUserSpecialDirs(parser.RegistryMultiParser):
  r"""Parser for extracting special folders from registry.

  Keys will come from HKEY_USERS and will list the Shell Folders and user's
  Environment key. We extract each subkey that matches on of our knowledge base
  attributes.

  Known folder GUIDs:
  http://msdn.microsoft.com/en-us/library/windows/desktop/dd378457(v=vs.85).aspx
  """
  output_types = ["User"]
  supported_artifacts = ["WindowsUserShellFolders"]
  # Required for environment variable expansion
  knowledgebase_dependencies = [
      "environ_systemdrive", "environ_systemroot", "users.userprofile"
  ]

  key_var_mapping = {
      "Shell Folders": {
          "{A520A1A4-1780-4FF6-BD18-167343C5AF16}": "localappdata_low",
          "Desktop": "desktop",
          "AppData": "appdata",
          "Local AppData": "localappdata",
          "Cookies": "cookies",
          "Cache": "internet_cache",
          "Recent": "recent",
          "Startup": "startup",
          "Personal": "personal",
      },
      "Environment": {
          "TEMP": "temp",
      },
      "Volatile Environment": {
          "USERDOMAIN": "userdomain",
      },
  }

  def ParseMultiple(self, stats, knowledge_base):
    """Parse each returned registry value."""
    user_dict = {}

    for stat in stats:
      sid_str = stat.pathspec.path.split("/", 3)[2]
      if SID_RE.match(sid_str):
        if sid_str not in user_dict:
          user_dict[sid_str] = rdf_client.User(sid=sid_str)

        if stat.registry_data.GetValue():
          # Look up in the mapping if we can use this entry to populate a user
          # attribute, and if so, set it.
          reg_key_name = stat.pathspec.Dirname().Basename()
          if reg_key_name in self.key_var_mapping:
            map_dict = self.key_var_mapping[reg_key_name]
            reg_key = stat.pathspec.Basename()
            kb_attr = map_dict.get(reg_key)
            if kb_attr:
              value = artifact_utils.ExpandWindowsEnvironmentVariables(
                  stat.registry_data.GetValue(), knowledge_base)
              value = artifact_utils.ExpandWindowsUserEnvironmentVariables(
                  value, knowledge_base, sid=sid_str)
              user_dict[sid_str].Set(kb_attr, value)

    # Now yield each user we found.
    return itervalues(user_dict)


class WinServicesParser(parser.RegistryValueParser):
  """Parser for Windows services values from the registry.

  See service key doco:
    http://support.microsoft.com/kb/103000
  """

  output_types = ["WindowsServiceInformation"]
  supported_artifacts = ["WindowsServices"]

  def __init__(self):
    # The key can be "services" or "Services" on different versions of windows.
    self.service_re = re.compile(
        r".*HKEY_LOCAL_MACHINE/SYSTEM/[^/]+/services/([^/]+)(/(.*))?$",
        re.IGNORECASE)
    super(WinServicesParser, self).__init__()

  def _GetServiceName(self, path):
    return self.service_re.match(path).group(1)

  def _GetKeyName(self, path):
    key_name = self.service_re.match(path).group(3)
    if key_name is None:
      return None
    return key_name.lower()

  def ParseMultiple(self, stats, knowledge_base):
    """Parse Service registry keys and return WindowsServiceInformation."""
    _ = knowledge_base
    services = {}
    field_map = {
        "Description": "description",
        "DisplayName": "display_name",
        "Group": "group_name",
        "DriverPackageId": "driver_package_id",
        "ErrorControl": "error_control",
        "ImagePath": "image_path",
        "ObjectName": "object_name",
        "Start": "startup_type",
        "Type": "service_type",
        "Parameters/ServiceDLL": "service_dll"
    }

    # Field map key should be converted to lowercase because key aquired through
    # self._GetKeyName could have some  characters in different case than the
    # field map, e.g. ServiceDLL and ServiceDll.
    field_map = {k.lower(): v for k, v in iteritems(field_map)}
    for stat in stats:

      # Ignore subkeys
      if not stat.HasField("registry_data"):
        continue

      service_name = self._GetServiceName(stat.pathspec.path)
      reg_key = os.path.dirname(stat.pathspec.path)
      service_info = rdf_client.WindowsServiceInformation(
          name=service_name, registry_key=reg_key)
      services.setdefault(service_name, service_info)

      key = self._GetKeyName(stat.pathspec.path)

      if key in field_map:
        try:
          services[service_name].Set(field_map[key],
                                     stat.registry_data.GetValue())
        except type_info.TypeValueError:

          # Flatten multi strings into a simple string
          if (stat.registry_type ==
              rdf_client_fs.StatEntry.RegistryType.REG_MULTI_SZ):
            services[service_name].Set(
                field_map[key],
                utils.SmartUnicode(stat.registry_data.GetValue()))
          else:
            # Log failures for everything else
            # TODO(user): change this to yield a ParserAnomaly object.
            dest_type = type(services[service_name].Get(field_map[key]))
            logging.debug("Wrong type set for %s:%s, expected %s, got %s",
                          stat.pathspec.path, stat.registry_data.GetValue(),
                          dest_type, type(stat.registry_data.GetValue()))

    return itervalues(services)


class WinTimezoneParser(parser.RegistryValueParser):
  """Parser for TimeZoneKeyName value."""

  output_types = ["RDFString"]
  supported_artifacts = ["WindowsTimezone"]

  def Parse(self, stat, knowledge_base):
    """Convert the timezone to Olson format."""
    _ = knowledge_base
    value = stat.registry_data.GetValue()
    result = ZONE_LIST.get(value.strip())
    if not result:
      yield rdfvalue.RDFString("Unknown (%s)" % value.strip())

    yield rdfvalue.RDFString(result)


# Prebuilt from HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT"
# \CurrentVersion\Time Zones\
# Note that these may not be consistent across Windows versions so may need
# adjustment in the future.
ZONE_LIST = {
    "IndiaStandardTime": "Asia/Kolkata",
    "EasternStandardTime": "EST5EDT",
    "EasternDaylightTime": "EST5EDT",
    "MountainStandardTime": "MST7MDT",
    "MountainDaylightTime": "MST7MDT",
    "PacificStandardTime": "PST8PDT",
    "PacificDaylightTime": "PST8PDT",
    "CentralStandardTime": "CST6CDT",
    "CentralDaylightTime": "CST6CDT",
    "SamoaStandardTime": "US/Samoa",
    "HawaiianStandardTime": "US/Hawaii",
    "AlaskanStandardTime": "US/Alaska",
    "MexicoStandardTime2": "MST7MDT",
    "USMountainStandardTime": "MST7MDT",
    "CanadaCentralStandardTime": "CST6CDT",
    "MexicoStandardTime": "CST6CDT",
    "CentralAmericaStandardTime": "CST6CDT",
    "USEasternStandardTime": "EST5EDT",
    "SAPacificStandardTime": "EST5EDT",
    "MalayPeninsulaStandardTime": "Asia/Kuching",
    "PacificSAStandardTime": "Canada/Atlantic",
    "AtlanticStandardTime": "Canada/Atlantic",
    "SAWesternStandardTime": "Canada/Atlantic",
    "NewfoundlandStandardTime": "Canada/Newfoundland",
    "AzoresStandardTime": "Atlantic/Azores",
    "CapeVerdeStandardTime": "Atlantic/Azores",
    "GMTStandardTime": "GMT",
    "GreenwichStandardTime": "GMT",
    "W.CentralAfricaStandardTime": "Europe/Belgrade",
    "W.EuropeStandardTime": "Europe/Belgrade",
    "CentralEuropeStandardTime": "Europe/Belgrade",
    "RomanceStandardTime": "Europe/Belgrade",
    "CentralEuropeanStandardTime": "Europe/Belgrade",
    "E.EuropeStandardTime": "Egypt",
    "SouthAfricaStandardTime": "Egypt",
    "IsraelStandardTime": "Egypt",
    "EgyptStandardTime": "Egypt",
    "NorthAsiaEastStandardTime": "Asia/Bangkok",
    "SingaporeStandardTime": "Asia/Bangkok",
    "ChinaStandardTime": "Asia/Bangkok",
    "W.AustraliaStandardTime": "Australia/Perth",
    "TaipeiStandardTime": "Asia/Bangkok",
    "TokyoStandardTime": "Asia/Tokyo",
    "KoreaStandardTime": "Asia/Seoul",
    "@tzres.dll,-10": "Atlantic/Azores",
    "@tzres.dll,-11": "Atlantic/Azores",
    "@tzres.dll,-12": "Atlantic/Azores",
    "@tzres.dll,-20": "Atlantic/Cape_Verde",
    "@tzres.dll,-21": "Atlantic/Cape_Verde",
    "@tzres.dll,-22": "Atlantic/Cape_Verde",
    "@tzres.dll,-40": "Brazil/East",
    "@tzres.dll,-41": "Brazil/East",
    "@tzres.dll,-42": "Brazil/East",
    "@tzres.dll,-70": "Canada/Newfoundland",
    "@tzres.dll,-71": "Canada/Newfoundland",
    "@tzres.dll,-72": "Canada/Newfoundland",
    "@tzres.dll,-80": "Canada/Atlantic",
    "@tzres.dll,-81": "Canada/Atlantic",
    "@tzres.dll,-82": "Canada/Atlantic",
    "@tzres.dll,-104": "America/Cuiaba",
    "@tzres.dll,-105": "America/Cuiaba",
    "@tzres.dll,-110": "EST5EDT",
    "@tzres.dll,-111": "EST5EDT",
    "@tzres.dll,-112": "EST5EDT",
    "@tzres.dll,-120": "EST5EDT",
    "@tzres.dll,-121": "EST5EDT",
    "@tzres.dll,-122": "EST5EDT",
    "@tzres.dll,-130": "EST5EDT",
    "@tzres.dll,-131": "EST5EDT",
    "@tzres.dll,-132": "EST5EDT",
    "@tzres.dll,-140": "CST6CDT",
    "@tzres.dll,-141": "CST6CDT",
    "@tzres.dll,-142": "CST6CDT",
    "@tzres.dll,-150": "America/Guatemala",
    "@tzres.dll,-151": "America/Guatemala",
    "@tzres.dll,-152": "America/Guatemala",
    "@tzres.dll,-160": "CST6CDT",
    "@tzres.dll,-161": "CST6CDT",
    "@tzres.dll,-162": "CST6CDT",
    "@tzres.dll,-170": "America/Mexico_City",
    "@tzres.dll,-171": "America/Mexico_City",
    "@tzres.dll,-172": "America/Mexico_City",
    "@tzres.dll,-180": "MST7MDT",
    "@tzres.dll,-181": "MST7MDT",
    "@tzres.dll,-182": "MST7MDT",
    "@tzres.dll,-190": "MST7MDT",
    "@tzres.dll,-191": "MST7MDT",
    "@tzres.dll,-192": "MST7MDT",
    "@tzres.dll,-200": "MST7MDT",
    "@tzres.dll,-201": "MST7MDT",
    "@tzres.dll,-202": "MST7MDT",
    "@tzres.dll,-210": "PST8PDT",
    "@tzres.dll,-211": "PST8PDT",
    "@tzres.dll,-212": "PST8PDT",
    "@tzres.dll,-220": "US/Alaska",
    "@tzres.dll,-221": "US/Alaska",
    "@tzres.dll,-222": "US/Alaska",
    "@tzres.dll,-230": "US/Hawaii",
    "@tzres.dll,-231": "US/Hawaii",
    "@tzres.dll,-232": "US/Hawaii",
    "@tzres.dll,-260": "GMT",
    "@tzres.dll,-261": "GMT",
    "@tzres.dll,-262": "GMT",
    "@tzres.dll,-271": "UTC",
    "@tzres.dll,-272": "UTC",
    "@tzres.dll,-280": "Europe/Budapest",
    "@tzres.dll,-281": "Europe/Budapest",
    "@tzres.dll,-282": "Europe/Budapest",
    "@tzres.dll,-290": "Europe/Warsaw",
    "@tzres.dll,-291": "Europe/Warsaw",
    "@tzres.dll,-292": "Europe/Warsaw",
    "@tzres.dll,-331": "Europe/Nicosia",
    "@tzres.dll,-332": "Europe/Nicosia",
    "@tzres.dll,-340": "Africa/Cairo",
    "@tzres.dll,-341": "Africa/Cairo",
    "@tzres.dll,-342": "Africa/Cairo",
    "@tzres.dll,-350": "Europe/Sofia",
    "@tzres.dll,-351": "Europe/Sofia",
    "@tzres.dll,-352": "Europe/Sofia",
    "@tzres.dll,-365": "Egypt",
    "@tzres.dll,-390": "Asia/Kuwait",
    "@tzres.dll,-391": "Asia/Kuwait",
    "@tzres.dll,-392": "Asia/Kuwait",
    "@tzres.dll,-400": "Asia/Baghdad",
    "@tzres.dll,-401": "Asia/Baghdad",
    "@tzres.dll,-402": "Asia/Baghdad",
    "@tzres.dll,-410": "Africa/Nairobi",
    "@tzres.dll,-411": "Africa/Nairobi",
    "@tzres.dll,-412": "Africa/Nairobi",
    "@tzres.dll,-434": "Asia/Tbilisi",
    "@tzres.dll,-435": "Asia/Tbilisi",
    "@tzres.dll,-440": "Asia/Muscat",
    "@tzres.dll,-441": "Asia/Muscat",
    "@tzres.dll,-442": "Asia/Muscat",
    "@tzres.dll,-447": "Asia/Baku",
    "@tzres.dll,-448": "Asia/Baku",
    "@tzres.dll,-449": "Asia/Baku",
    "@tzres.dll,-450": "Asia/Yerevan",
    "@tzres.dll,-451": "Asia/Yerevan",
    "@tzres.dll,-452": "Asia/Yerevan",
    "@tzres.dll,-460": "Asia/Kabul",
    "@tzres.dll,-461": "Asia/Kabul",
    "@tzres.dll,-462": "Asia/Kabul",
    "@tzres.dll,-471": "Asia/Yekaterinburg",
    "@tzres.dll,-472": "Asia/Yekaterinburg",
    "@tzres.dll,-511": "Asia/Aqtau",
    "@tzres.dll,-512": "Asia/Aqtau",
    "@tzres.dll,-570": "Asia/Chongqing",
    "@tzres.dll,-571": "Asia/Chongqing",
    "@tzres.dll,-572": "Asia/Chongqing",
    "@tzres.dll,-650": "Australia/Darwin",
    "@tzres.dll,-651": "Australia/Darwin",
    "@tzres.dll,-652": "Australia/Darwin",
    "@tzres.dll,-660": "Australia/Adelaide",
    "@tzres.dll,-661": "Australia/Adelaide",
    "@tzres.dll,-662": "Australia/Adelaide",
    "@tzres.dll,-670": "Australia/Sydney",
    "@tzres.dll,-671": "Australia/Sydney",
    "@tzres.dll,-672": "Australia/Sydney",
    "@tzres.dll,-680": "Australia/Brisbane",
    "@tzres.dll,-681": "Australia/Brisbane",
    "@tzres.dll,-682": "Australia/Brisbane",
    "@tzres.dll,-721": "Pacific/Port_Moresby",
    "@tzres.dll,-722": "Pacific/Port_Moresby",
    "@tzres.dll,-731": "Pacific/Fiji",
    "@tzres.dll,-732": "Pacific/Fiji",
    "@tzres.dll,-840": "America/Argentina/Buenos_Aires",
    "@tzres.dll,-841": "America/Argentina/Buenos_Aires",
    "@tzres.dll,-842": "America/Argentina/Buenos_Aires",
    "@tzres.dll,-880": "UTC",
    "@tzres.dll,-930": "UTC",
    "@tzres.dll,-931": "UTC",
    "@tzres.dll,-932": "UTC",
    "@tzres.dll,-1010": "Asia/Aqtau",
    "@tzres.dll,-1020": "Asia/Dhaka",
    "@tzres.dll,-1021": "Asia/Dhaka",
    "@tzres.dll,-1022": "Asia/Dhaka",
    "@tzres.dll,-1070": "Asia/Tbilisi",
    "@tzres.dll,-1120": "America/Cuiaba",
    "@tzres.dll,-1140": "Pacific/Fiji",
    "@tzres.dll,-1460": "Pacific/Port_Moresby",
    "@tzres.dll,-1530": "Asia/Yekaterinburg",
    "@tzres.dll,-1630": "Europe/Nicosia",
    "@tzres.dll,-1660": "America/Bahia",
    "@tzres.dll,-1661": "America/Bahia",
    "@tzres.dll,-1662": "America/Bahia",
    "Central Standard Time": "CST6CDT",
    "Pacific Standard Time": "PST8PDT",
}
