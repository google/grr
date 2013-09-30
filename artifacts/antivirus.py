#!/usr/bin/env python
"""Artifacts that are specific to Antivirus."""

from grr.lib import artifact_lib

# Shorcut to make things cleaner.
Artifact = artifact_lib.GenericArtifact   # pylint: disable=g-bad-name
Collector = artifact_lib.Collector        # pylint: disable=g-bad-name

################################################################################
#  Sophos Artifacts
################################################################################


class SophosMacQuarantineFiles(Artifact):
  """Sophos Infected files for OSX."""
  SUPPORTED_OS = ["Darwin"]
  LABELS = ["Antivirus"]
  COLLECTORS = [
      Collector(action="GetFile",
                args={"path": "/Users/Shared/Infected"})
  ]


class SophosWinQuarantineFiles(Artifact):
  """Sophos Infected files for Windows."""
  SUPPORTED_OS = ["Windows"]
  LABELS = ["Antivirus"]
  COLLECTORS = [
      Collector(action="GetFile",
                args={"path": "%%allusersappdata%%\\Sophos\\Sophos Anti-Virus"
                      "\\INFECTED\\*"})
  ]


class SophosMacLogs(Artifact):
  """Sophos Logs for OSX."""
  SUPPORTED_OS = ["Darwin"]
  LABELS = ["Antivirus", "Logs"]
  COLLECTORS = [
      Collector(action="GetFile",
                args={"path": "/Library/Logs/Sophos*.log"})
  ]


class SophosWinLogs(Artifact):
  """Sophos Logs for Windows."""
  SUPPORTED_OS = ["Windows"]
  LABELS = ["Antivirus", "Logs"]
  COLLECTORS = [
      Collector(action="GetFile",
                args={"path": "%%allusersappdata%%\\Sophos\\Sophos Anti-Virus"
                      "\\Logs\\*"})
  ]
