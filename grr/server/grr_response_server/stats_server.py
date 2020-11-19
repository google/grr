#!/usr/bin/env python
# Lint as: python3
"""Stats server implementation."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import errno
from http import server as http_server
import logging
import socket
import threading

import prometheus_client

from grr_response_core import config
from grr_response_core.lib import utils
from grr_response_server import base_stats_server

StatsServerHandler = prometheus_client.MetricsHandler


# Python's standard HTTP server implementation is broken and will work through
# a IPv4 socket. This means, that on IPv6 only environment, the code will fail
# to create the socket and fail in mysterious ways.
#
# We hack around this by overriding the `address_family` that `HTTPServer` uses
# to create the socket and always use IPv6 (it was introduced in 1995, so it is
# safe to expect that every modern stack will support it already).
class IPv6HTTPServer(http_server.HTTPServer):

  address_family = socket.AF_INET6


class StatsServer(base_stats_server.BaseStatsServer):
  """A statistics server that exposes a minimal, custom /varz route."""

  def __init__(self, port):
    """Instantiates a new StatsServer.

    Args:
      port: The TCP port that the server should listen to.
    """
    super().__init__(port)
    self._http_server = None
    self._server_thread = None

  def Start(self):
    """Start HTTPServer."""
    try:
      self._http_server = IPv6HTTPServer(("::1", self.port), StatsServerHandler)
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


@utils.RunOnce
def InitializeStatsServerOnce():
  """Starts up a varz server after everything is registered.

  StatsServer implementation may be overridden. If there's a "stats_server"
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
        logging.info(e)
        continue
      raise
