#!/usr/bin/env python
"""Central registry for all the client's monitored metrics."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.stats import stats_utils


def GetMetadata():
  """Returns a list of MetricMetadata for the client's metrics."""
  return [
      stats_utils.CreateCounterMetadata("grr_client_received_bytes"),
      stats_utils.CreateCounterMetadata("grr_client_sent_bytes"),
      stats_utils.CreateGaugeMetadata("grr_client_cpu_usage", str),
      stats_utils.CreateGaugeMetadata("grr_client_io_usage", str)
  ]
