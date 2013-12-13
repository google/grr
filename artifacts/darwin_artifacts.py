#!/usr/bin/env python
"""Artifacts that are specific to Darwin/OSX."""

from grr.lib import artifact_lib

# Shorcut to make things cleaner.
Artifact = artifact_lib.GenericArtifact   # pylint: disable=g-bad-name
Collector = artifact_lib.Collector        # pylint: disable=g-bad-name


class OSXServices(Artifact):
  """Collect running services from the servicemanagement framework."""
  SUPPORTED_OS = ["Darwin"]
  LABELS = ["Software"]
  COLLECTORS = [
      Collector(action="RunGrrClientAction",
                args={"client_action": "EnumerateRunningServices"})
      ]

