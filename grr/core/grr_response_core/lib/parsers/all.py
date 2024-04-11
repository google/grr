#!/usr/bin/env python
"""A module for registering all known parsers."""

from grr_response_core.lib import parsers
from grr_response_core.lib.parsers import cron_file_parser
from grr_response_core.lib.parsers import linux_cmd_parser
from grr_response_core.lib.parsers import linux_file_parser
from grr_response_core.lib.parsers import linux_release_parser
from grr_response_core.lib.parsers import osx_file_parser
from grr_response_core.lib.parsers import osx_launchd
from grr_response_core.lib.parsers import windows_persistence
from grr_response_core.lib.parsers import windows_registry_parser
from grr_response_core.lib.parsers import wmi_parser


def Register():
  """Adds all known parsers to the registry."""
  # pyformat: disable

  # Command parsers.
  parsers.SINGLE_RESPONSE_PARSER_FACTORY.Register(
      "Dpkg", linux_cmd_parser.DpkgCmdParser)
  parsers.SINGLE_RESPONSE_PARSER_FACTORY.Register(
      "Dmidecode", linux_cmd_parser.DmidecodeCmdParser)
  parsers.SINGLE_RESPONSE_PARSER_FACTORY.Register(
      "OsxSpHardware", osx_file_parser.OSXSPHardwareDataTypeParser)
  parsers.SINGLE_RESPONSE_PARSER_FACTORY.Register(
      "Rpm", linux_cmd_parser.RpmCmdParser)

  # WMI query parsers.
  parsers.MULTI_RESPONSE_PARSER_FACTORY.Register(
      "WmiInstalledSoftware", wmi_parser.WMIInstalledSoftwareParser)
  parsers.MULTI_RESPONSE_PARSER_FACTORY.Register(
      "WmiHotfixesSoftware", wmi_parser.WMIHotfixesSoftwareParser)
  parsers.MULTI_RESPONSE_PARSER_FACTORY.Register(
      "WmiUser", wmi_parser.WMIUserParser)
  parsers.MULTI_RESPONSE_PARSER_FACTORY.Register(
      "WmiLogicalDisks", wmi_parser.WMILogicalDisksParser)
  parsers.MULTI_RESPONSE_PARSER_FACTORY.Register(
      "WmiCsp", wmi_parser.WMIComputerSystemProductParser)

  # Registry value parsers.
  parsers.SINGLE_RESPONSE_PARSER_FACTORY.Register(
      "WinCcs", windows_registry_parser.CurrentControlSetKBParser)
  parsers.SINGLE_RESPONSE_PARSER_FACTORY.Register(
      "WinCodepage", windows_registry_parser.CodepageParser)
  parsers.SINGLE_RESPONSE_PARSER_FACTORY.Register(
      "WinEnvironment", windows_registry_parser.WinEnvironmentParser)
  parsers.SINGLE_RESPONSE_PARSER_FACTORY.Register(
      "WinSystemDrive", windows_registry_parser.WinSystemDriveParser)
  parsers.SINGLE_RESPONSE_PARSER_FACTORY.Register(
      "WinSystemRoot", windows_registry_parser.WinSystemRootParser)
  parsers.SINGLE_RESPONSE_PARSER_FACTORY.Register(
      "WinTimezone", windows_registry_parser.WinTimezoneParser)

  # Registry parsers.
  parsers.SINGLE_RESPONSE_PARSER_FACTORY.Register(
      "WinAllUsersProfileEnvVar",
      windows_registry_parser.AllUsersProfileEnvironmentVariable)
  parsers.SINGLE_RESPONSE_PARSER_FACTORY.Register(
      "WinProfileDirEnvVar",
      windows_registry_parser.ProfilesDirectoryEnvironmentVariable)
  parsers.SINGLE_RESPONSE_PARSER_FACTORY.Register(
      "WinUserSids",
      windows_registry_parser.WinUserSids)

  # Artifact file parsers.
  parsers.SINGLE_RESPONSE_PARSER_FACTORY.Register(
      "DarwinPersistenceMechanism",
      osx_launchd.DarwinPersistenceMechanismsParser)
  parsers.SINGLE_RESPONSE_PARSER_FACTORY.Register(
      "WindowsPersistenceMechanism",
      windows_persistence.WindowsPersistenceMechanismsParser)

  # File parsers.
  parsers.SINGLE_FILE_PARSER_FACTORY.Register(
      "CronTab", cron_file_parser.CronTabParser)
  parsers.SINGLE_FILE_PARSER_FACTORY.Register(
      "Passwd", linux_file_parser.PasswdParser)
  parsers.SINGLE_FILE_PARSER_FACTORY.Register(
      "OsxLaunchdPlist", osx_file_parser.OSXLaunchdPlistParser)
  parsers.SINGLE_FILE_PARSER_FACTORY.Register(
      "OSXInstallHistoryPlist", osx_file_parser.OSXInstallHistoryPlistParser)

  # File multi-parsers.
  parsers.MULTI_FILE_PARSER_FACTORY.Register(
      "LinuxReleaseInfo", linux_release_parser.LinuxReleaseParser)

  # pyformat: enable
