#!/usr/bin/env python
"""A module for registering all known parsers."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib import parsers
from grr_response_core.lib.parsers import chrome_history
from grr_response_core.lib.parsers import config_file
from grr_response_core.lib.parsers import cron_file_parser
from grr_response_core.lib.parsers import firefox3_history
from grr_response_core.lib.parsers import ie_history
from grr_response_core.lib.parsers import linux_cmd_parser
from grr_response_core.lib.parsers import linux_file_parser
from grr_response_core.lib.parsers import linux_pam_parser
from grr_response_core.lib.parsers import linux_release_parser
from grr_response_core.lib.parsers import linux_service_parser
from grr_response_core.lib.parsers import linux_software_parser
from grr_response_core.lib.parsers import linux_sysctl_parser
from grr_response_core.lib.parsers import osx_file_parser
from grr_response_core.lib.parsers import osx_launchd
from grr_response_core.lib.parsers import rekall_artifact_parser
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
      "Mount", config_file.MountCmdParser)
  parsers.SINGLE_RESPONSE_PARSER_FACTORY.Register(
      "OsxSpHardware", osx_file_parser.OSXSPHardwareDataTypeParser)
  parsers.SINGLE_RESPONSE_PARSER_FACTORY.Register(
      "Ps", linux_cmd_parser.PsCmdParser)
  parsers.SINGLE_RESPONSE_PARSER_FACTORY.Register(
      "Rpm", linux_cmd_parser.RpmCmdParser)
  parsers.SINGLE_RESPONSE_PARSER_FACTORY.Register(
      "SshdConfig", config_file.SshdConfigCmdParser)
  parsers.SINGLE_RESPONSE_PARSER_FACTORY.Register(
      "Sysctl", linux_sysctl_parser.SysctlCmdParser)
  parsers.SINGLE_RESPONSE_PARSER_FACTORY.Register(
      "YumList", linux_cmd_parser.YumListCmdParser)
  parsers.SINGLE_RESPONSE_PARSER_FACTORY.Register(
      "YumRepolist", linux_cmd_parser.YumRepolistCmdParser)

  # Grep parsers.
  parsers.SINGLE_RESPONSE_PARSER_FACTORY.Register(
      "Passwd", linux_file_parser.PasswdBufferParser)
  parsers.SINGLE_RESPONSE_PARSER_FACTORY.Register(
      "Netgroup", linux_file_parser.NetgroupBufferParser)

  # WMI query parsers.
  parsers.SINGLE_RESPONSE_PARSER_FACTORY.Register(
      "WmiEventConsumer", wmi_parser.WMIEventConsumerParser)
  parsers.SINGLE_RESPONSE_PARSER_FACTORY.Register(
      "WmiInstalledSoftware", wmi_parser.WMIInstalledSoftwareParser)
  parsers.SINGLE_RESPONSE_PARSER_FACTORY.Register(
      "WmiHotfixesSoftware", wmi_parser.WMIHotfixesSoftwareParser)
  parsers.SINGLE_RESPONSE_PARSER_FACTORY.Register(
      "WmiUser", wmi_parser.WMIUserParser)
  parsers.SINGLE_RESPONSE_PARSER_FACTORY.Register(
      "WmiLogicalDisks", wmi_parser.WMILogicalDisksParser)
  parsers.SINGLE_RESPONSE_PARSER_FACTORY.Register(
      "WmiCsp", wmi_parser.WMIComputerSystemProductParser)
  parsers.SINGLE_RESPONSE_PARSER_FACTORY.Register(
      "WmiInterfaces", wmi_parser.WMIInterfacesParser)

  # Registry value parsers.
  parsers.SINGLE_RESPONSE_PARSER_FACTORY.Register(
      "WinCcs", windows_registry_parser.CurrentControlSetKBParser)
  parsers.SINGLE_RESPONSE_PARSER_FACTORY.Register(
      "WinCodepage", windows_registry_parser.CodepageParser)
  parsers.SINGLE_RESPONSE_PARSER_FACTORY.Register(
      "WinEnvironment", windows_registry_parser.WinEnvironmentParser)
  parsers.SINGLE_RESPONSE_PARSER_FACTORY.Register(
      "WinServices", windows_registry_parser.WinServicesParser)
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

  # Rekall parsers.
  parsers.SINGLE_RESPONSE_PARSER_FACTORY.Register(
      "RekallPsList", rekall_artifact_parser.RekallPsListParser)
  parsers.SINGLE_RESPONSE_PARSER_FACTORY.Register(
      "RekallVad", rekall_artifact_parser.RekallVADParser)

  # Registry multi-parsers.
  parsers.MULTI_RESPONSE_PARSER_FACTORY.Register(
      "WinUserSpecialDirs", windows_registry_parser.WinUserSpecialDirs)

  # Artifact file multi-parsers.
  parsers.MULTI_RESPONSE_PARSER_FACTORY.Register(
      "OsxUsers", osx_file_parser.OSXUsersParser)

  # File parsers.
  parsers.SINGLE_FILE_PARSER_FACTORY.Register(
      "ChromeHistory", chrome_history.ChromeHistoryParser)
  parsers.SINGLE_FILE_PARSER_FACTORY.Register(
      "CronAtAllAllowDeny", config_file.CronAtAllowDenyParser)
  parsers.SINGLE_FILE_PARSER_FACTORY.Register(
      "CronTab", cron_file_parser.CronTabParser)
  parsers.SINGLE_FILE_PARSER_FACTORY.Register(
      "FirefoxHistory", firefox3_history.FirefoxHistoryParser)
  parsers.SINGLE_FILE_PARSER_FACTORY.Register(
      "IeHistory", ie_history.IEHistoryParser)
  parsers.SINGLE_FILE_PARSER_FACTORY.Register(
      "LinuxWtmp", linux_file_parser.LinuxWtmpParser)
  parsers.SINGLE_FILE_PARSER_FACTORY.Register(
      "Mtab", config_file.MtabParser)
  parsers.SINGLE_FILE_PARSER_FACTORY.Register(
      "Netgroup", linux_file_parser.NetgroupParser)
  parsers.SINGLE_FILE_PARSER_FACTORY.Register(
      "NfsExports", config_file.NfsExportsParser)
  parsers.SINGLE_FILE_PARSER_FACTORY.Register(
      "Ntpd", config_file.NtpdParser)
  parsers.SINGLE_FILE_PARSER_FACTORY.Register(
      "PackageSource", config_file.PackageSourceParser)
  parsers.SINGLE_FILE_PARSER_FACTORY.Register(
      "Passwd", linux_file_parser.PasswdParser)
  parsers.SINGLE_FILE_PARSER_FACTORY.Register(
      "Path", linux_file_parser.PathParser)
  parsers.SINGLE_FILE_PARSER_FACTORY.Register(
      "SshdConfigFile", config_file.SshdConfigParser)
  parsers.SINGLE_FILE_PARSER_FACTORY.Register(
      "Sudoers", config_file.SudoersParser)
  parsers.SINGLE_FILE_PARSER_FACTORY.Register(
      "OsxLaunchdPlist", osx_file_parser.OSXLaunchdPlistParser)
  parsers.SINGLE_FILE_PARSER_FACTORY.Register(
      "OSXInstallHistoryPlist", osx_file_parser.OSXInstallHistoryPlistParser)

  try:
    from debian import deb822  # pylint: disable=g-import-not-at-top
    parsers.SINGLE_FILE_PARSER_FACTORY.Register(
        "DpkgStatusParser",
        lambda: linux_software_parser.DebianPackagesStatusParser(deb822))
  except ImportError:
    pass


  # File multi-parsers.
  parsers.MULTI_FILE_PARSER_FACTORY.Register(
      "LinuxBaseShadow", linux_file_parser.LinuxBaseShadowParser)
  parsers.MULTI_FILE_PARSER_FACTORY.Register(
      "LinuxLsbInit", linux_service_parser.LinuxLSBInitParser)
  parsers.MULTI_FILE_PARSER_FACTORY.Register(
      "LinuxXinetd", linux_service_parser.LinuxXinetdParser)
  parsers.MULTI_FILE_PARSER_FACTORY.Register(
      "LinuxSysvInit", linux_service_parser.LinuxSysVInitParser)
  parsers.MULTI_FILE_PARSER_FACTORY.Register(
      "LinuxPam", linux_pam_parser.PAMParser)
  parsers.MULTI_FILE_PARSER_FACTORY.Register(
      "LinuxRelease", linux_release_parser.LinuxReleaseParser)
  parsers.MULTI_FILE_PARSER_FACTORY.Register(
      "PciDevicesInfo", linux_file_parser.PCIDevicesInfoParser)
  parsers.MULTI_FILE_PARSER_FACTORY.Register(
      "ProcSys", linux_sysctl_parser.ProcSysParser)
  parsers.MULTI_FILE_PARSER_FACTORY.Register(
      "Rsyslog", config_file.RsyslogParser)

  # pyformat: enable
