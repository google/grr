#!/usr/bin/env python
"""Test helper classes to test GRR WSGI app."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import logging
import threading


import requests
from werkzeug import serving

from grr_response_core import config
from grr_response_core.lib import utils
from grr_response_server.gui import wsgiapp


class ServerThread(threading.Thread):
  """A class to run the wsgi server in another thread."""

  keep_running = True
  daemon = True

  def __init__(self, port, **kwargs):
    super(ServerThread, self).__init__(**kwargs)
    self.ready_to_serve = threading.Event()
    self.port = port

  def StartAndWaitUntilServing(self):
    self.start()
    if not self.ready_to_serve.wait(60.0):
      raise RuntimeError("Server thread did not initialize properly.")

  def Stop(self):
    # The Werkzeug server is pretty bad at shutting down. The only way to make
    # this work without the danger of blocking forever is to switch the
    # shutdown_signal flag and send one more request.
    self.server.shutdown_signal = True
    try:
      requests.get("http://localhost:%d" % self.port, timeout=0.3)
    except (requests.exceptions.ConnectionError,
            requests.exceptions.ReadTimeout):
      pass

  def run(self):
    """Run the WSGI server in a thread."""
    logging.info("Listening on port %d.", self.port)

    ssl_context = None
    if config.CONFIG["AdminUI.enable_ssl"]:
      cert_file = config.CONFIG["AdminUI.ssl_cert_file"]
      if not cert_file:
        raise ValueError("Need a valid cert file to enable SSL.")

      key_file = config.CONFIG["AdminUI.ssl_key_file"]
      if not key_file:
        raise ValueError("Need a valid key file to enable SSL.")

      ssl_context = (cert_file, key_file)

    # Werkzeug only handles IPv6 if ":" is in the host (i.e. we pass
    # an IPv6 ip).
    ip = utils.ResolveHostnameToIP("localhost", self.port)
    self.server = serving.make_server(
        ip,
        self.port,
        wsgiapp.AdminUIApp().WSGIHandler(),
        ssl_context=ssl_context)

    # We want to notify other threads that we are now ready to serve right
    # before we enter the serving loop.
    self.ready_to_serve.set()
    while self.keep_running:
      self.server.handle_request()
