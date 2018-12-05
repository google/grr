#!/usr/bin/env python
"""Client startup routines."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_client import client_logging
from grr_response_client import client_metrics
from grr_response_core import config
from grr_response_core.config import contexts
from grr_response_core.lib import communicator
from grr_response_core.lib import config_lib
from grr_response_core.lib import registry
from grr_response_core.lib.parsers import all as all_parsers
from grr_response_core.stats import default_stats_collector
from grr_response_core.stats import stats_collector_instance


def ClientInit():
  """Run all startup routines for the client."""
  metric_metadata = client_metrics.GetMetadata()
  metric_metadata.extend(communicator.GetMetricMetadata())
  stats_collector_instance.Set(
      default_stats_collector.DefaultStatsCollector(metric_metadata))

  config_lib.SetPlatformArchContext()
  config_lib.ParseConfigCommandLine()

  client_logging.LogInit()
  all_parsers.Register()
  registry.Init()

  if not config.CONFIG.ContextApplied(contexts.CLIENT_BUILD_CONTEXT):
    config.CONFIG.Persist("Client.labels")
    config.CONFIG.Persist("Client.proxy_servers")
    config.CONFIG.Persist("Client.tempdir_roots")
