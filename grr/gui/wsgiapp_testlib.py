#!/usr/bin/env python
"""Test helper classes to test GRR WSGI app."""



import logging
import threading


from werkzeug import serving

from grr.gui import wsgiapp
from grr.lib import utils


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

  def run(self):
    """Run the WSGI server in a thread."""
    logging.info("Listening on port %d.", self.port)

    # Werkzeug only handles IPv6 if ":" is in the host (i.e. we pass
    # an IPv6 ip).
    ip = utils.ResolveHostnameToIP("localhost", self.port)
    server = serving.make_server(ip, self.port,
                                 wsgiapp.AdminUIApp().WSGIHandler())

    # We want to notify other threads that we are now ready to serve right
    # before we enter the serving loop.
    self.ready_to_serve.set()
    while self.keep_running:
      server.handle_request()
