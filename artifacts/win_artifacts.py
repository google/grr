#!/usr/bin/env python
"""Artifacts that are specific to Windows."""

from grr.lib import artifact_lib
from grr.lib import constants

# Shorcut to make things cleaner.
Artifact = artifact_lib.GenericArtifact   # pylint: disable=g-bad-name
Collector = artifact_lib.Collector        # pylint: disable=g-bad-name

# pylint: disable=g-line-too-long


################################################################################
#  Windows specific conditions
################################################################################


# TODO(user): Deprecate these once we move to the objectfilter scheme.
def VistaOrNewer(knowledge_base):
  """Is the client newer than Windows Vista?"""
  return (knowledge_base.os_major_version >=
          constants.MAJOR_VERSION_WINDOWS_VISTA)


def NotVistaOrNewer(client):
  return not VistaOrNewer(client)


################################################################################
#  Core Windows system artifacts
################################################################################


class WinTimeZone(Artifact):
  """The timezone of the system in Olson format."""
  URLS = ["https://code.google.com/p/winreg-kb/wiki/TimeZoneKeys"]
  SUPPORTED_OS = ["Windows"]
  LABELS = ["KnowledgeBase"]
  COLLECTORS = [
      Collector(action="GetRegistryValue",
                args={"path": r"%%current_control_set%%\Control\TimeZoneInformation\TimeZoneKeyName"})]
  PROVIDES = "time_zone"


class WinCodePage(Artifact):
  """The codepage of the system."""
  URLS = ["http://en.wikipedia.org/wiki/Windows_code_page"]
  SUPPORTED_OS = ["Windows"]
  LABELS = ["KnowledgeBase"]
  COLLECTORS = [
      Collector(action="GetRegistryValue",
                args={"path": r"%%current_control_set%%\Control\Nls\CodePage\ACP"})]
  PROVIDES = "code_page"


class WinDomainName(Artifact):
  """The Windows domain the system is connected to."""
  URLS = []
  SUPPORTED_OS = ["Windows"]
  LABELS = ["KnowledgeBase"]
  COLLECTORS = [
      Collector(action="GetRegistryValue",
                args={"path": r"%%current_control_set%%\Services\Tcpip\Parameters\Domain"})]
  PROVIDES = "domain"


class CurrentControlSet(Artifact):
  """The control set the system is currently using."""
  URLS = ["https://code.google.com/p/winreg-kb/wiki/SystemKeys"]
  SUPPORTED_OS = ["Windows"]
  LABELS = ["KnowledgeBase"]
  COLLECTORS = [
      Collector(action="GetRegistryValue",
                args={"path": r"HKEY_LOCAL_MACHINE\SYSTEM\Select\Current"})]
  PROVIDES = "current_control_set"


class SystemRoot(Artifact):
  """The base system directory."""
  URLS = ["http://environmentvariables.org/SystemRoot"]
  COLLECTORS = [Collector(action="Bootstrap")]
  SUPPORTED_OS = ["Windows"]
  LABELS = ["KnowledgeBase"]
  PROVIDES = "environ_systemroot"


class ProgramFiles(Artifact):
  """The %ProgramFiles% environment variable."""
  URLS = ["http://environmentvariables.org/ProgramFiles"]
  SUPPORTED_OS = ["Windows"]
  LABELS = ["KnowledgeBase"]
  COLLECTORS = [
      Collector(action="GetRegistryValue",
                args={"path": r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\ProgramFilesDir"})]
  PROVIDES = "environ_programfiles"


class ProgramFilesx86(Artifact):
  """The %ProgramFiles (x86)% environment variable."""
  URLS = ["http://environmentvariables.org/ProgramFiles"]
  LABELS = ["KnowledgeBase"]
  COLLECTORS = [
      Collector(action="GetRegistryValue",
                args={"path": r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\ProgramFilesDir (x86)"})]
  SUPPORTED_OS = ["Windows"]
  PROVIDES = "environ_programfilesx86"


class TempEnvironmentVariable(Artifact):
  """The %TEMP% environment variable."""
  URLS = ["http://environmentvariables.org/WinDir"]
  SUPPORTED_OS = ["Windows"]
  LABELS = ["KnowledgeBase"]
  PROVIDES = "environ_temp"
  COLLECTORS = [
      Collector(action="GetRegistryValue",
                args={"path": r"%%current_control_set%%\Control\Session Manager\Environment\TEMP"})]


class WinDirEnvironmentVariable(Artifact):
  """The %WinDIr% environment variable."""
  URLS = ["http://environmentvariables.org/WinDir"]
  SUPPORTED_OS = ["Windows"]
  LABELS = ["KnowledgeBase"]
  PROVIDES = "environ_windir"
  COLLECTORS = [
      Collector(action="GetRegistryValue",
                args={"path": r"%%current_control_set%%\Control\Session Manager\Environment\windir"})]


class WinPathEnvironmentVariable(Artifact):
  """The %PATH% environment variable."""
  URLS = ["http://environmentvariables.org/WinDir"]
  SUPPORTED_OS = ["Windows"]
  LABELS = ["KnowledgeBase"]
  PROVIDES = "environ_path"
  COLLECTORS = [
      Collector(action="GetRegistryValue",
                args={"path": r"%%current_control_set%%\Control\Session Manager\Environment\Path"})]


class SystemDriveEnvironmentVariable(Artifact):
  """The %SystemDrive% environment variable."""
  URLS = ["http://environmentvariables.org/SystemDrive"]
  SUPPORTED_OS = ["Windows"]
  LABELS = ["KnowledgeBase"]
  PROVIDES = "environ_systemdrive"
  COLLECTORS = [Collector(action="Bootstrap")]


class AllUsersAppDataEnvironmentVariable(Artifact):
  """The %ProgramData% environment variable."""
  URLS = ["http://environmentvariables.org/ProgramData"]
  SUPPORTED_OS = ["Windows"]
  LABELS = ["KnowledgeBase"]
  PROVIDES = "environ_allusersappdata"
  COLLECTORS = [
      Collector(action="GetRegistryValue",
                args={"path": r"HKEY_LOCAL_MACHINE\Software\Microsoft\Windows NT\CurrentVersion\ProfileList\ProgramData"})]


class AllUsersProfileEnvironmentVariable(Artifact):
  """The %AllUsersProfile% environment variable."""
  URLS = ["http://support.microsoft.com/kb//214653"]
  SUPPORTED_OS = ["Windows"]
  LABELS = ["KnowledgeBase"]
  PROVIDES = "environ_allusersprofile"
  COLLECTORS = [
      Collector(action="GetRegistryKeys",
                args={"paths": [r"HKEY_LOCAL_MACHINE\Software\Microsoft\Windows NT\CurrentVersion\ProfileList\ProfilesDirectory",
                                r"HKEY_LOCAL_MACHINE\Software\Microsoft\Windows NT\CurrentVersion\ProfileList\AllUsersProfile"]})
      ]


################################################################################
#  Event Log Artifacts for Vista + versions of Windows
################################################################################


class AbstractEventLogEvtx(Artifact):
  URLS = ["http://www.forensicswiki.org/wiki/Windows_XML_Event_Log_(EVTX)"]
  CONDITIONS = [VistaOrNewer]
  SUPPORTED_OS = ["Windows"]
  LABELS = ["Logs"]
  PATH_VARS = {"log_path": "%%environ_systemroot%%\\System32\\winevt\\Logs"}
  PROCESSORS = ["EvtxLogParser"]


class ApplicationEventLogEvtx(AbstractEventLogEvtx):
  """Windows Application Event Log for Vista or newer systems."""
  COLLECTORS = [
      Collector(action="GetFile",
                args={"path": "%%environ_systemroot%%\\System32\\winevt\\Logs\\Application.evtx"})]


class SystemEventLogEvtx(AbstractEventLogEvtx):
  """Windows System Event Log for Vista or newer systems."""
  COLLECTORS = [
      Collector(action="GetFile", args={"path": "{log_path}\\System.evtx"})]


class SecurityEventLogEvtx(AbstractEventLogEvtx):
  """Windows Security Event Log for Vista or newer systems."""
  COLLECTORS = [
      Collector(action="GetFile", args={"path": "{log_path}\\Security.evtx"})]


class TerminalServicesEventLogEvtx(AbstractEventLogEvtx):
  """Windows TerminalServices Event Log."""
  DESCRIPTION_LONG = """
Contains information about logins, connects, disconnects made via
RDP/TerminalServices to the machine.
"""
  COLLECTORS = [
      Collector(action="GetFile",
                args={"path": "{log_path}\\Microsoft-Windows-TerminalServices-LocalSessionManager%4Operational.evtx"})]


################################################################################
#  Event Log Artifacts for older versions of Windows
################################################################################


class AbstractEventLog(Artifact):
  URLS = ["http://www.forensicswiki.org/wiki/Windows_Event_Log_(EVT)"]
  SUPPORTED_OS = ["Windows"]
  CONDITIONS = [NotVistaOrNewer]
  LABELS = ["Logs"]


class AbstractWMIArtifact(Artifact):
  SUPPORTED_OS = ["Windows"]
  CONDITIONS = [VistaOrNewer]


class ApplicationEventLog(AbstractEventLog):
  """Windows Application Event Log."""
  COLLECTORS = [
      Collector(
          action="GetFile",
          args={"path": "%%environ_systemroot%%\\System32\\winevt\\Logs\\AppEvent.evt"}
          )]


class SystemEventLog(AbstractEventLog):
  """Windows System Event Log."""
  COLLECTORS = [
      Collector(
          action="GetFile",
          args={"path": "%%environ_systemroot%%\\System32\\winevt\\Logs\\SysEvent.evt"}
          )]


class SecurityEventLog(AbstractEventLog):
  """Windows Security Event Log."""
  COLLECTORS = [
      Collector(
          action="GetFile",
          args={"path": "%%environ_systemroot%%\\System32\\winevt\\Logs\\SecEvent.evt"}
          )]


class WindowsWMIInstalledSoftware(AbstractWMIArtifact):
  """Extract the installed software on Windows via WMI."""
  LABELS = ["Software"]

  COLLECTORS = [
      Collector(action="WMIQuery",
                args={"query": "SELECT Name, Vendor, Description, InstallDate, InstallDate2, Version"
                      " from Win32_Product"}
               )
  ]


class WindowsDrivers(AbstractWMIArtifact):
  """Extract the installed drivers on Windows via WMI."""
  LABELS = ["Software"]

  COLLECTORS = [
      Collector(action="WMIQuery",
                args={"query": "SELECT DisplayName, Description, InstallDate, Name, PathName, Status, State, ServiceType "
                      "from Win32_SystemDriver"}
               )
  ]
