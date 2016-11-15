#!/usr/bin/env python
"""This is a selenium test harness used interactively with Selenium IDE."""

import socket
import threading
from wsgiref import simple_server


import logging
from grr.gui import django_lib
# pylint: disable=unused-import
from grr.gui import tests_init
# pylint: enable=unused-import

from grr.lib import config_lib
from grr.lib import flags
from grr.lib import ipshell
from grr.lib import startup


class DjangoThread(threading.Thread):
  """A class to run the wsgi server in another thread."""

  keep_running = True
  daemon = True

  def __init__(self, port, **kwargs):
    super(DjangoThread, self).__init__(**kwargs)
    self.base_url = "http://127.0.0.1:%d" % port
    self.ready_to_serve = threading.Event()
    self.port = port

  def StartAndWaitUntilServing(self):
    self.start()
    if not self.ready_to_serve.wait(60.0):
      raise RuntimeError("Djangothread did not initialize properly.")

  def run(self):
    """Run the django server in a thread."""
    logging.info("Base URL is %s", self.base_url)
    port = self.port
    logging.info("Django listening on port %d.", port)
    try:
      # Make a simple reference implementation WSGI server
      server = simple_server.make_server("0.0.0.0", port,
                                         django_lib.GetWSGIHandler())
    except socket.error as e:
      raise socket.error("Error while listening on port %d: %s." %
                         (port, str(e)))

    # We want to notify other threads that we are now ready to serve right
    # before we enter the serving loop.
    self.ready_to_serve.set()
    while self.keep_running:
      server.handle_request()


def main(_):
  """Run the main test harness."""
  startup.TestInit()

  # Start up a server in another thread
  trd = DjangoThread(config_lib.CONFIG["AdminUI.port"])
  trd.StartAndWaitUntilServing()

  user_ns = dict()
  user_ns.update(globals())
  user_ns.update(locals())

  # Wait in the shell so selenium IDE can be used.
  ipshell.IPShell(argv=[], user_ns=user_ns)


if __name__ == "__main__":
  flags.StartMain(main)
