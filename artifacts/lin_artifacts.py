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


class DebianPackages(Artifact):
  """Linux output of dpkg --list."""
  SUPPORTED_OS = ["Linux"]
  LABELS = ["Software"]

  COLLECTORS = [
      Collector(action="RunCommand",
                args={"cmd": "/usr/bin/dpkg", "args": ["--list"]},
               )
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
