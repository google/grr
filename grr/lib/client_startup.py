#!/usr/bin/env python
"""Client startup routines."""

from grr.lib import config_lib
from grr.lib import log
from grr.lib import registry
from grr.lib import stats


def ClientInit():
  """Run all startup routines for the client."""
  if stats.STATS is None:
    stats.STATS = stats.StatsCollector()

  config_lib.SetPlatformArchContext()
  config_lib.ParseConfigCommandLine()

  log.LogInit()
  registry.Init()
