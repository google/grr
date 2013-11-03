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
                args={"path": r"%%current_control_set%%\Control\TimeZoneInformation\StandardName"})]
  PROVIDES = "time_zone"


class AvailableTimeZones(Artifact):
  """The timezones avaialable on the system."""
  URLS = ["https://code.google.com/p/winreg-kb/wiki/TimeZoneKeys"]
  SUPPORTED_OS = ["Windows"]
  COLLECTORS = [
      Collector(action="GetRegistryKeys",
                args={"path_list": [r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Time Zones\*\*"]})]


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
                args={"path_list": [r"HKEY_LOCAL_MACHINE\Software\Microsoft\Windows NT\CurrentVersion\ProfileList\ProfilesDirectory",
                                    r"HKEY_LOCAL_MACHINE\Software\Microsoft\Windows NT\CurrentVersion\ProfileList\AllUsersProfile"]})
      ]


################################################################################
#  Windows user related information
################################################################################


class WindowsRegistryProfiles(Artifact):
  """Get SIDs for all users on the system with profiles present in the registry.

  This looks in the Windows registry where the profiles are stored and retrieves
  the paths for each profile.
  """
  URLS = ["http://msdn.microsoft.com/en-us/library/windows/desktop/bb776892(v=vs.85).aspx"]
  SUPPORTED_OS = ["Windows"]
  LABELS = ["Users", "KnowledgeBase"]
  COLLECTORS = [
      Collector(action="GetRegistryKeys",
                args={"path_list": [r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList\*\ProfileImagePath"]}
               )
  ]
  PROVIDES = ["users.sid", "users.userprofile", "users.homedir"]


class WindowsWMIProfileUsers(Artifact):
  """Get user information based on known user's SID.

  This artifact optimizes retrieval of user information by limiting the WMI
  query to users for which we have a SID for. Specifically this solves the issue
  that in a domain setting, querying for all users via WMI will give you the
  list of all local and domain accounts which means a large data transfer from
  an Active Directory server.

  This artifact relies on having the SID field users.sid populated knowledge
  base.
  """
  URLS = ["http://msdn.microsoft.com/en-us/library/windows/desktop/aa394507(v=vs.85).aspx"]
  SUPPORTED_OS = ["Windows"]
  LABELS = ["Users", "KnowledgeBase"]
  COLLECTORS = [
      Collector(action="WMIQuery",
                args={"query": "SELECT * FROM Win32_UserAccount "
                               "WHERE name='%%users.username%%'"}
               )
  ]
  PROVIDES = ["users.username", "users.userdomain", "users.sid"]


class WindowsWMIUsers(Artifact):
  """Get all users the system knows about via WMI.

  Note that in a domain setup, this will probably return all users in the
  domain which will be expensive and slow. Consider WindowsWMIProfileUsers
  instead.
  """
  URLS = ["http://msdn.microsoft.com/en-us/library/windows/desktop/aa394507(v=vs.85).aspx"]
  LABELS = ["Users"]
  SUPPORTED_OS = ["Windows"]

  COLLECTORS = [
      Collector(action="WMIQuery",
                args={"query": "SELECT * FROM Win32_UserAccount"}
               )
  ]


class UserShellFolders(Artifact):
  """The Shell Folders information for Windows users."""
  SUPPORTED_OS = ["Windows"]
  LABELS = ["KnowledgeBase"]
  PROVIDES = ["users.cookies", "users.appdata", "users.personal",
              "users.startup", "users.homedir", "users.desktop",
              "users.local_settings", "users.internet_cache",
              "users.localappdata", "users.recent", "users.userprofile",
              "users.temp"]

  COLLECTORS = [
      Collector(action="GetRegistryKeys",
                args={"path_list": [r"HKEY_USERS\%%users.sid%%\Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders\*",
                                    r"HKEY_USERS\%%users.sid%%\Environment\*"]})
      ]


################################################################################
#  Event Log Artifacts for Vista + versions of Windows
################################################################################


class AbstractEventLogEvtx(Artifact):
  URLS = ["http://www.forensicswiki.org/wiki/Windows_XML_Event_Log_(EVTX)"]
  CONDITIONS = [VistaOrNewer]
  SUPPORTED_OS = ["Windows"]
  LABELS = ["Logs"]


class ApplicationEventLogEvtx(AbstractEventLogEvtx):
  """Windows Application Event Log for Vista or newer systems."""
  COLLECTORS = [
      Collector(action="GetFile",
                args={"path": r"%%environ_systemroot%%\System32\winevt\Logs\Application.evtx"})]


class SystemEventLogEvtx(AbstractEventLogEvtx):
  """Windows System Event Log for Vista or newer systems."""
  COLLECTORS = [
      Collector(action="GetFile", args={"path": r"%%environ_systemroot%%\System32\winevt\Logs\System.evtx"})]


class SecurityEventLogEvtx(AbstractEventLogEvtx):
  """Windows Security Event Log for Vista or newer systems."""
  COLLECTORS = [
      Collector(action="GetFile", args={"path": r"%%environ_systemroot%%\System32\winevt\Logs\Security.evtx"})]


class TerminalServicesEventLogEvtx(AbstractEventLogEvtx):
  """Windows TerminalServices Event Log."""
  DESCRIPTION_LONG = """
Contains information about logins, connects, disconnects made via
RDP/TerminalServices to the machine.
"""
  COLLECTORS = [
      Collector(action="GetFile",
                args={"path": r"%%environ_systemroot%%\System32\winevt\Logs\Microsoft-Windows-TerminalServices-LocalSessionManager%4Operational.evtx"})]


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
          args={"path": r"%%environ_systemroot%%\System32\winevt\Logs\AppEvent.evt"}
          )]


class SystemEventLog(AbstractEventLog):
  """Windows System Event Log."""
  COLLECTORS = [
      Collector(
          action="GetFile",
          args={"path": r"%%environ_systemroot%%\System32\winevt\Logs\SysEvent.evt"}
          )]


class SecurityEventLog(AbstractEventLog):
  """Windows Security Event Log."""
  COLLECTORS = [
      Collector(
          action="GetFile",
          args={"path": r"%%environ_systemroot%%\System32\winevt\Logs\SecEvent.evt"}
          )]


################################################################################
#  Software Artifacts
################################################################################


class WindowsWMIInstalledSoftware(AbstractWMIArtifact):
  """Extract the installed software on Windows via WMI."""
  LABELS = ["Software"]

  COLLECTORS = [
      Collector(action="WMIQuery",
                args={"query": "SELECT Name, Vendor, Description, InstallDate, InstallDate2, Version "
                               "from Win32_Product"}
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


class WindowsHotFixes(AbstractWMIArtifact):
  """Extract the installed hotfixes on Windows via WMI."""
  LABELS = ["Software"]

  COLLECTORS = [
      Collector(action="WMIQuery",
                args={"query": "SELECT * "
                               "from Win32_QuickFixEngineering"}
               )
  ]


class WindowsRunKeys(Artifact):
  """Collect windows run keys."""
  LABELS = ["Software"]
  SUPPORTED_OS = ["Windows"]
  COLLECTORS = [
      Collector(action="GetRegistryKeys",
                args={"path_list":
                      [r"HKEY_USERS\%%users.sid%%\Software\Microsoft\Windows\CurrentVersion\Run\*",
                       r"HKEY_USERS\%%users.sid%%\Software\Microsoft\Windows\CurrentVersion\RunOnce\*",
                       r"HKEY_LOCAL_MACHINE\Software\Microsoft\Windows\CurrentVersion\Run\*",
                       r"HKEY_LOCAL_MACHINE\Software\Microsoft\Windows\CurrentVersion\RunOnce\*"]})]


################################################################################
#  User Artifacts
################################################################################


class WindowsAdminUsers(AbstractWMIArtifact):
  """Extract the Aministrators on Windows via WMI."""
  LABELS = ["Software"]

  COLLECTORS = [
      Collector(action="WMIQuery",
                args={"query": "SELECT * "
                               "from Win32_GroupUser where Name = \"Administrators\""}
               )
  ]


class WindowsLoginUsers(AbstractWMIArtifact):
  """Extract the Login Users on Windows via WMI.

  If on a domain this will query the domain which may take a long time and
  create load on a domain controller.
  <script>alert(1)</script>
  """
  LABELS = ["Software"]

  COLLECTORS = [
      Collector(action="WMIQuery",
                args={"query": "SELECT * "
                               "from Win32_GroupUser where Name = \"login_users\""}
               )
  ]


class WMIProcessList(AbstractWMIArtifact):
  """Extract the process list on Windows via WMI."""
  LABELS = ["Software"]

  COLLECTORS = [
      Collector(action="WMIQuery",
                args={"query": "SELECT * "
                               "from Win32_Process"}
               )
  ]


################################################################################
#  Network Artifacts
################################################################################


class WinHostsFile(Artifact):
  """The Windows hosts file."""
  COLLECTORS = [
      Collector(action="GetFile",
                args={"path": "%%environ_systemroot%%\\System32\\Drivers\\etc\\hosts"})]
