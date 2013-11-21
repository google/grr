#!/usr/bin/env python
"""Artifacts that run Volatility plugins."""

from grr.lib import artifact_lib

# Shorcut to make things cleaner.
Artifact = artifact_lib.GenericArtifact   # pylint: disable=g-bad-name
Collector = artifact_lib.Collector        # pylint: disable=g-bad-name

# pylint: disable=g-line-too-long


class VolatilityPsList(Artifact):
  """Process listing using Volatility."""
  URLS = ["https://code.google.com/p/volatility/wiki/CommandReference#pslist"]
  SUPPORTED_OS = []
  LABELS = ["Volatility", "Processes"]
  COLLECTORS = [
      Collector(action="VolatilityPlugin",
                args={"plugin": "pslist",
                      "args": {}})]

