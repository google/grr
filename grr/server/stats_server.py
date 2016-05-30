#!/usr/bin/env python
"""Stats server implementation."""



import BaseHTTPServer

import collections
import json
import socket
import threading


import logging

from grr.lib import config_lib
from grr.lib import registry
from grr.lib import stats


class StatsServerHandler(BaseHTTPServer.BaseHTTPRequestHandler):
  """Default stats server implementation."""

  def _JSONMetricValue(self, metric_info, value):
    if metric_info.metric_type == stats.MetricType.EVENT:
      return dict(sum=value.sum,
                  counter=value.count,
                  bins=value.bins,
                  bins_heights=collections.OrderedDict(value.bins_heights))
    else:
      return value

  def do_GET(self):  # pylint: disable=g-bad-name
    if self.path == "/varz":
      self.send_response(200)
      self.send_header("Content-type", "application/json")
      self.end_headers()

      results = {}
      for name, metric_info in stats.STATS.GetAllMetricsMetadata().iteritems():
        info_dict = dict(metric_type=metric_info.metric_type)
        if metric_info.value_type:
          info_dict["value_type"] = metric_info.value_type.__name__
        if metric_info.docstring:
          info_dict["docstring"] = metric_info.docstring
        if metric_info.units:
          info_dict["units"] = metric_info.units

        if metric_info.fields_defs:
          info_dict["fields_defs"] = metric_info.fields_defs
          value = {}
          all_fields = stats.STATS.GetAllMetricFields(name)
          for f in all_fields:
            value[f] = self._JSONMetricValue(
                metric_info,
                stats.STATS.GetMetricValue(name, fields=f))
        else:
          value = self._JSONMetricValue(metric_info,
                                        stats.STATS.GetMetricValue(name))

        results[name] = dict(info=info_dict, value=value)

      encoder = json.JSONEncoder()
      self.wfile.write(encoder.encode(results))
    else:
      self.send_error(403, "Access forbidden: %s" % self.path)


class StatsServer(object):

  def __init__(self, port):
    self.port = port

  def Start(self):
    """Start HTTPServer."""
    # Use the same number of available ports as the adminui is using. If we
    # have 10 available for adminui we will need 10 for the stats server.
    adminui_max_port = config_lib.CONFIG.Get("AdminUI.port_max",
                                             config_lib.CONFIG["AdminUI.port"])

    additional_ports = adminui_max_port - config_lib.CONFIG["AdminUI.port"]
    max_port = self.port + additional_ports

    for port in range(self.port, max_port + 1):
      # Make a simple reference implementation WSGI server
      try:
        server = BaseHTTPServer.HTTPServer(("", port), StatsServerHandler)
        break
      except socket.error as e:
        if e.errno == socket.errno.EADDRINUSE and port < max_port:
          logging.info("Port %s in use, trying %s", port, port + 1)
        else:
          raise

    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()


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
    port = config_lib.CONFIG["Monitoring.http_port"]
    if port != 0:
      logging.info("Starting monitoring server on port %d.", port)
      # pylint: disable=g-import-not-at-top
      from grr.lib import local as local_overrides
      # pylint: enable=g-import-not-at-top
      if "stats_server" in dir(local_overrides):
        stats_server = local_overrides.stats_server.StatsServer(port)
        logging.debug("Using local StatsServer from %s", local_overrides)
      else:
        stats_server = StatsServer(port)

      stats_server.Start()
    else:
      logging.info("Monitoring server disabled.")
