#!/usr/bin/env python
"""This is a selenium test harness used interactively with Selenium IDE."""

import copy
import threading
import urllib
from wsgiref import simple_server


# pylint: disable=unused-import,g-bad-import-order
from grr.gui import admin_ui
# pylint: enable=unused-import,g-bad-import-order

from django.core.handlers import wsgi

import logging

from grr.lib import access_control
from grr.lib import config_lib
from grr.lib import data_store
from grr.lib import flags
from grr.lib import ipshell
from grr.lib import registry
from grr.lib import startup
from grr.lib import test_lib


class DjangoThread(threading.Thread):
  """A class to run the wsgi server in another thread."""

  keep_running = True

  def __init__(self, **kwargs):
    super(DjangoThread, self).__init__(**kwargs)
    self.base_url = "http://127.0.0.1:%d" % config_lib.CONFIG["AdminUI.port"]

  def run(self):
    """Run the django server in a thread."""
    logging.info("Base URL is %s", self.base_url)

    # Make a simple reference implementation WSGI server
    server = simple_server.make_server("0.0.0.0",
                                       config_lib.CONFIG["AdminUI.port"],
                                       wsgi.WSGIHandler())
    while self.keep_running:
      server.handle_request()

  def Stop(self):
    self.keep_running = False
    # Force a request so the socket leaves accept()
    urllib.urlopen(self.base_url + "/quitmenow").read()
    self.join()


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
    self.token = access_control.ACLToken("Test", "Make fixtures.")
    self.token.supervisor = True

    if data_store.DB.__class__.__name__ == "FakeDataStore":
      self.RestoreFixtureFromCache()
    else:
      self.BuildFixture()

  def BuildFixture(self):
    logging.info("Making fixtures")

    # Make 10 clients
    for i in range(0, 10):
      test_lib.ClientFixture("C.%016X" % i, token=self.token)

  def RestoreFixtureFromCache(self):
    """Restores test fixture (by building it or using a cached version)."""
    if RunTestsInit.fixture_cache is None:
      # Make a data store snapshot.
      db = data_store.DB.subjects
      data_store.DB.subjects = {}

      self.BuildFixture()
      (RunTestsInit.fixture_cache,
       data_store.DB.subjects) = (data_store.DB.subjects, db)

    # Restore the fixture from the cache
    data_store.DB.subjects.update(copy.deepcopy(RunTestsInit.fixture_cache))


class TestPluginInit(registry.InitHook):
  """Load the test plugins after django is initialized."""
  pre = ["DjangoInit"]

  def RunOnce(self):
    # pylint: disable=unused-variable,C6204
    from grr.gui.plugins import tests
    # pylint: enable=unused-variable,C6204


def main(_):
  """Run the main test harness."""
  # For testing we use the test config file.
  flags.FLAGS.config = config_lib.CONFIG["Test.config"]

  # We are running a test so let the config system know that.
  config_lib.CONFIG.AddContext(
      "Test Context",
      "Context applied when we run tests.")

  startup.TestInit()

  # Tests must be imported after django is initialized.
  # pylint: disable=g-import-not-at-top,unused-variable
  from grr.gui.plugins import tests
  # pylint: enable=g-import-not-at-top,unused-variable

  # Start up a server in another thread
  trd = DjangoThread()
  trd.start()
  try:
    user_ns = dict()
    user_ns.update(globals())
    user_ns.update(locals())

    # Wait in the shell so selenium IDE can be used.
    ipshell.IPShell(argv=[], user_ns=user_ns)
  finally:
    # Kill the server thread
    trd.Stop()

if __name__ == "__main__":
  flags.StartMain(main)
