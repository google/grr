#!/usr/bin/env python
"""Artifacts that are specific to Linux."""

from grr.lib import artifact_lib

# Shorcut to make things cleaner.
Artifact = artifact_lib.GenericArtifact   # pylint: disable=g-bad-name
Collector = artifact_lib.Collector        # pylint: disable=g-bad-name

################################################################################
#  Linux Log Artifacts
################################################################################


class AuthLog(Artifact):
  """Linux auth log file."""
  SUPPORTED_OS = ["Linux"]
  LABELS = ["Logs", "Authentication"]
  COLLECTORS = [
      Collector(action="GetFile",
                args={"path": "/var/log/auth.log"})
  ]


class Wtmp(Artifact):
  """Linux wtmp file."""
  SUPPORTED_OS = ["Linux"]
  LABELS = ["Logs", "Authentication"]

  COLLECTORS = [
      Collector(action="GetFile",
                args={"path": "/var/log/wtmp"})
  ]


class LinuxPasswd(Artifact):
  """Linux passwd file."""
  SUPPORTED_OS = ["Linux"]
  LABELS = ["Authentication"]

  COLLECTORS = [
      Collector(action="GetFile",
                args={"path": "/etc/passwd"},
               )
  ]


################################################################################
#  Security Check Artifacts
################################################################################


class DebianPackagesList(Artifact):
  """Linux output of dpkg --list."""
  SUPPORTED_OS = ["Linux"]
  LABELS = ["Software"]

  COLLECTORS = [
      Collector(action="RunCommand",
                args={"cmd": "/usr/bin/dpkg", "args": ["--list"]},
               )
  ]


class DebianPackagesStatus(Artifact):
  """Linux dpkg status file."""
  SUPPORTED_OS = ["Linux"]
  LABELS = ["Software"]

  COLLECTORS = [
      Collector(action="GetFile",
                args={"path": "/var/lib/dpkg/status"},
               )
  ]


class RedhatPackagesList(Artifact):
  """Linux output of rpm -qa."""
  SUPPORTED_OS = ["Linux"]
  LABELS = ["Software"]

  COLLECTORS = [
      Collector(action="RunCommand",
                args={"cmd": "/bin/rpm", "args": ["-qa"]},
               )
  ]


class LoginPolicyConfiguration(Artifact):
  """Linux files related to login policy configuration."""
  SUPPORTED_OS = ["Linux"]
  LABELS = ["Authentication", "Configuration Files"]

  COLLECTORS = [
      Collector(action="GetFiles",
                args={"path_list": ["/etc/netgroup", "/etc/nsswitch.conf",
                                    "/etc/passwd", "/etc/shadow",
                                    "/etc/security/access.conf",
                                    "/root/.k5login"]},
               )
  ]


class SudoersConfiguration(Artifact):
  """Linux sudoers configuration."""
  SUPPORTED_OS = ["Linux"]
  LABELS = ["Authentication", "Configuration Files"]

  COLLECTORS = [
      Collector(action="GetFiles",
                args={"path_list": ["/etc/sudoers"]},
               )
  ]


class HostAccessPolicyConfiguration(Artifact):
  """Linux files related to host access policy configuration."""
  SUPPORTED_OS = ["Linux"]
  LABELS = ["Configuration Files"]

  COLLECTORS = [
      Collector(action="GetFiles",
                args={"path_list": ["/etc/hosts.allow", "/etc/hosts.deny"]},
               )
  ]


class RootUserShellConfigs(Artifact):
  """Linux root shell configuration files."""
  SUPPORTED_OS = ["Linux"]
  LABELS = ["Configuration Files"]

  COLLECTORS = [
      Collector(action="GetFiles",
                args={"path_list": ["/root/.bashrc", "/root/.cshrc",
                                    "/root/.ksh", "/root/.logout",
                                    "/root/.profile", "/root/.tcsh",
                                    "/root/.zlogin", "/root/.zlogout",
                                    "/root/.zprofile", "/root/.zprofile"]},
               )
  ]


class GlobalShellConfigs(Artifact):
  """Linux global shell configuration files."""
  SUPPORTED_OS = ["Linux"]
  LABELS = ["Configuration Files"]

  COLLECTORS = [
      Collector(action="GetFiles",
                args={"path_list": ["/etc/bash.bashrc", "/etc/csh.cshrc",
                                    "/etc/csh.login", "/etc/csh.logout",
                                    "/etc/profile", "/etc/zsh/zlogin",
                                    "/etc/zsh/zlogout", "/etc/zsh/zprofile",
                                    "/etc/zsh/zshenv", "/etc/zsh/zshrc"]},
               )
  ]
