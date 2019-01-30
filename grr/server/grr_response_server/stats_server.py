#!/usr/bin/env python
"""Stats server implementation."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import collections
import errno
import json
import logging
import socket
import threading

from future.builtins import range
from future.moves.urllib import parse as urlparse
from future.utils import iteritems
from http import server as http_server

import prometheus_client

from grr_response_core import config
from grr_response_core.lib import registry
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import stats as rdf_stats
from grr_response_core.stats import stats_collector_instance
from grr_response_server import base_stats_server


def _JSONMetricValue(metric_info, value):
  if metric_info.metric_type == rdf_stats.MetricMetadata.MetricType.EVENT:
    return dict(
        sum=value.sum,
        counter=value.count,
        bins_heights=collections.OrderedDict(value.bins_heights))
  else:
    return value


def BuildVarzJsonString():
  """Builds Varz JSON string from all stats metrics."""

  results = {}
  for name, metric_info in iteritems(
      stats_collector_instance.Get().GetAllMetricsMetadata()):
    info_dict = dict(metric_type=metric_info.metric_type.name)
    if metric_info.value_type:
      info_dict["value_type"] = metric_info.value_type.name
    if metric_info.docstring:
      info_dict["docstring"] = metric_info.docstring
    if metric_info.units:
      info_dict["units"] = metric_info.units.name

    if metric_info.fields_defs:
      info_dict["fields_defs"] = []
      for field_def in metric_info.fields_defs:
        info_dict["fields_defs"].append((field_def.field_name,
                                         utils.SmartStr(field_def.field_type)))

      value = {}
      all_fields = stats_collector_instance.Get().GetMetricFields(name)
      for f in all_fields:
        joined_fields = ":".join(utils.SmartStr(fname) for fname in f)
        value[joined_fields] = _JSONMetricValue(
            metric_info,
            stats_collector_instance.Get().GetMetricValue(name, fields=f))
    else:
      value = _JSONMetricValue(
          metric_info,
          stats_collector_instance.Get().GetMetricValue(name))

    results[name] = dict(info=info_dict, value=value)

  encoder = json.JSONEncoder()
  return encoder.encode(results)


class StatsServerHandler(http_server.BaseHTTPRequestHandler):
  """Default stats server implementation."""

  def do_GET(self):  # pylint: disable=g-bad-name
    # Per Prometheus docs: /metrics is the default path for scraping.
    if self.path == "/metrics":
      # TODO: This code is copied from
      # prometheus_client.MetricsHandler. Because MetricsHandler is an old-style
      # class and dispatching to different BaseHTTPRequestHandlers is
      # surprisingly hard, we copied the code instead of calling it. After a
      # deprecation period, the /varz route will be removed and
      # StatsServerHandler can be replaced by prometheus_client.MetricsHandler.
      pc_registry = prometheus_client.REGISTRY
      params = urlparse.parse_qs(urlparse.urlparse(self.path).query)
      encoder, content_type = prometheus_client.exposition.choose_encoder(
          self.headers.get("Accept"))
      if "name[]" in params:
        pc_registry = pc_registry.restricted_registry(params["name[]"])
      try:
        output = encoder(pc_registry)
      except:
        self.send_error(500, "error generating metric output")
        raise
      self.send_response(200)
      self.send_header("Content-Type", content_type)
      self.end_headers()
      self.wfile.write(output)
    elif self.path == "/varz":
      self.send_response(200)
      self.send_header("Content-type", "application/json")
      self.end_headers()

      self.wfile.write(BuildVarzJsonString())
    elif self.path == "/healthz":
      self.send_response(200)
    else:
      self.send_error(404, "Not found")


class StatsServer(base_stats_server.BaseStatsServer):
  """A statistics server that exposes a minimal, custom /varz route."""

  def __init__(self, port):
    """Instantiates a new StatsServer.

    Args:
      port: The TCP port that the server should listen to.
    """
    super(StatsServer, self).__init__(port)
    self._http_server = None
    self._server_thread = None

  def Start(self):
    """Start HTTPServer."""
    try:
      self._http_server = http_server.HTTPServer(("", self.port),
                                                 StatsServerHandler)
    except socket.error as e:
      if e.errno == errno.EADDRINUSE:
        raise base_stats_server.PortInUseError(self.port)
      else:
        raise

    self._server_thread = threading.Thread(
        target=self._http_server.serve_forever)
    self._server_thread.daemon = True
    self._server_thread.start()

  def Stop(self):
    """Stops serving statistics."""
    self._http_server.shutdown()
    self._server_thread.join()


class StatsServerInit(registry.InitHook):
  """Starts up a varz server after everything is registered."""

  def RunOnce(self):
    """Main method of this registry hook.

    StatsServer implementation may be overriden. If there's a "stats_server"
    module present in grr/local directory then
    grr.local.stats_server.StatsServer implementation will be used instead of
    a default one.
    """

    # Figure out which port to use.
    port = config.CONFIG["Monitoring.http_port"]
    if not port:
      logging.info("Monitoring server disabled.")
      return

    # TODO(user): Implement __contains__ for GrrConfigManager.
    max_port = config.CONFIG.Get("Monitoring.http_port_max", None)
    if max_port is None:
      # Use the same number of available ports as the adminui is using. If we
      # have 10 available for adminui we will need 10 for the stats server.
      adminui_max_port = config.CONFIG.Get("AdminUI.port_max",
                                           config.CONFIG["AdminUI.port"])
      max_port = port + adminui_max_port - config.CONFIG["AdminUI.port"]

    try:
      # pylint: disable=g-import-not-at-top
      from grr_response_server.local import stats_server
      # pylint: enable=g-import-not-at-top
      server_cls = stats_server.StatsServer
      logging.debug("Using local StatsServer")
    except ImportError:
      logging.debug("Using default StatsServer")
      server_cls = StatsServer

    for port in range(port, max_port + 1):
      try:
        logging.info("Starting monitoring server on port %d.", port)
        server_obj = server_cls(port)
        server_obj.Start()
        return
      except base_stats_server.PortInUseError as e:
        if e.port < max_port:
          logging.info(e.message)
          continue
        raise
