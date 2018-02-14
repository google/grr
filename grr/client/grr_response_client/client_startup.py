#!/usr/bin/env python
"""Client startup routines."""

from grr_response_client import client_logging
from grr.lib import config_lib
from grr.lib import registry
from grr.lib import stats


def ClientInit():
  """Run all startup routines for the client."""
  if stats.STATS is None:
    stats.STATS = stats.StatsCollector()

  config_lib.SetPlatformArchContext()
  config_lib.ParseConfigCommandLine()

  client_logging.LogInit()
  registry.Init()
