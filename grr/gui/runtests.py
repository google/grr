#!/usr/bin/env python
"""This is a selenium test harness used interactively with Selenium IDE."""

import socket
import threading
from wsgiref import simple_server


import logging

# pylint: disable=g-bad-import-order
from grr.gui import django_lib
# pylint: enable=g-bad-import-order

from grr.lib import access_control
from grr.lib import aff4
from grr.lib import client_index
from grr.lib import config_lib
from grr.lib import data_store
from grr.lib import flags
from grr.lib import ipshell
from grr.lib import registry
from grr.lib import startup
from grr.lib import test_lib
from grr.lib.aff4_objects import aff4_grr
from grr.lib.rdfvalues import client as rdf_client


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


class RunTestsInit(registry.InitHook):
  """Init hook that sets up test fixtures."""

  pre = ["AFF4InitHook"]

  # We cache all the AFF4 objects created by this fixture so its faster to
  # recreate it between tests.
  fixture_cache = None

  def Run(self):
    """Run the hook setting up fixture and security mananger."""
    # Install the mock security manager so we can trap errors in interactive
    # mode.
    data_store.DB.security_manager = test_lib.MockSecurityManager()
    self.token = access_control.ACLToken(
        username="test", reason="Make fixtures.")
    self.token = self.token.SetUID()

    self.BuildFixture()

  def BuildFixture(self):
    for i in range(10):
      client_id = rdf_client.ClientURN("C.%016X" % i)
      with aff4.FACTORY.Create(
          client_id, aff4_grr.VFSGRRClient, mode="rw",
          token=self.token) as client_obj:
        aff4.FACTORY.Create(
            client_index.MAIN_INDEX,
            aff4_type=client_index.ClientIndex,
            mode="rw",
            token=self.token).AddClient(client_obj)


class TestPluginInit(registry.InitHook):
  """Load the test plugins after django is initialized."""
  pre = ["DjangoInit"]

  def RunOnce(self):
    # pylint: disable=unused-variable,g-import-not-at-top
    from grr.gui.plugins import tests
    # pylint: enable=unused-variable,g-import-not-at-top


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
