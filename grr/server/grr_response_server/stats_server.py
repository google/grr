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


from builtins import range  # pylint: disable=redefined-builtin
from future.utils import iteritems
from http import server as http_server

from grr_response_core import config
from grr_response_core.lib import registry
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import stats as rdf_stats
from grr_response_core.stats import stats_collector_instance


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
    if self.path == "/varz":
      self.send_response(200)
      self.send_header("Content-type", "application/json")
      self.end_headers()

      self.wfile.write(BuildVarzJsonString())
    else:
      self.send_error(403, "Access forbidden: %s" % self.path)


class StatsServer(object):

  def __init__(self, port):
    self.port = port

  def Start(self):
    """Start HTTPServer."""
    # Use the same number of available ports as the adminui is using. If we
    # have 10 available for adminui we will need 10 for the stats server.
    adminui_max_port = config.CONFIG.Get("AdminUI.port_max",
                                         config.CONFIG["AdminUI.port"])

    additional_ports = adminui_max_port - config.CONFIG["AdminUI.port"]
    max_port = self.port + additional_ports

    for port in range(self.port, max_port + 1):
      # Make a simple reference implementation WSGI server
      try:
        server = http_server.HTTPServer(("", port), StatsServerHandler)
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
    port = config.CONFIG["Monitoring.http_port"]
    if not port:
      logging.info("Monitoring server disabled.")
      return

    max_port = config.CONFIG.Get("Monitoring.http_port_max",
                                 config.CONFIG["Monitoring.http_port"])

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
      except socket.error as e:
        if e.errno == errno.EADDRINUSE and port < max_port:
          logging.info("Port %s in use", port)
          continue
        raise
