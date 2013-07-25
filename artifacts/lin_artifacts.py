#!/usr/bin/env python
# Copyright 2012 Google Inc. All Rights Reserved.

"""Artifacts that are specific to Linux."""




from grr.lib import artifact

# Shorcut to make things cleaner.
Artifact = artifact.GenericArtifact   # pylint: disable=g-bad-name
Collector = artifact.Collector        # pylint: disable=g-bad-name


################################################################################
#  Linux Log Artifacts
################################################################################


class AuthLog(Artifact):
  """Linux auth log file."""
  SUPPORTED_OS = ["Linux"]
  LABELS = ["Logs", "Auth"]
  COLLECTORS = [
      Collector(action="GetFile",
                args={"path": "/var/log/auth.log"})
  ]


class Wtmp(Artifact):
  """Linux wtmp file."""
  SUPPORTED_OS = ["Linux"]
  LABELS = ["Logs", "Auth"]

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
  PROCESSOR = "DpkgCmdParser"

