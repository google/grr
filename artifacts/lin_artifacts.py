#!/usr/bin/env python
# Copyright 2012 Google Inc. All Rights Reserved.

"""Artifacts that are specific to Windows."""




from grr.lib import artifact

# Shorcut to make things cleaner.
Artifact = artifact.GenericArtifact   # pylint: disable=C6409
Collector = artifact.Collector        # pylint: disable=C6409


################################################################################
#  Linux Log Artifacts
################################################################################


class AuthLog(Artifact):
  """Linux auth log file."""
  SUPPORTED_OS = ["Linux"]
  LABELS = ["Logs", "Auth"]
  COLLECTORS = [
      Collector(action="GetFile", args={"path": "/var/log/auth.log"})
  ]


class Wtmp(Artifact):
  """Linux wtmp file."""
  SUPPORTED_OS = ["Linux"]
  LABELS = ["Logs", "Auth"]

  COLLECTORS = [
      Collector(action="GetFile", args={"path": "/var/log/wtmp"})
  ]
  PROCESSORS = ["WtmpParser"]
