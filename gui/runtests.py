#!/usr/bin/env python

# Copyright 2011 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""This is a selenium test harness."""
import socket
import threading
import unittest
import urllib
from wsgiref import simple_server

from django.core.handlers import wsgi
from django.core.management import setup_environ
from IPython import Shell
from grr.client import conf
from grr.client import conf as flags
import logging
from grr.gui import settings
from grr.lib import aff4
from grr.lib import fake_data_store
from grr.lib import test_lib
from grr.lib.flows import general


flags.DEFINE_bool("interactive", False,
                  "run interactively (for use with Selenium IDE)")

flags.DEFINE_integer("port", 8000,
                     "port to listen on")

FLAGS = flags.FLAGS


class DjangoThread(threading.Thread):
  """A class to run the wsgi server in another thread."""

  keep_running = True

  def run(self):
    """Run the django server in a thread."""

    self.base_url = "http://%s:%d" % (socket.getfqdn(), FLAGS.port)
    logging.info("Base URL is %s", self.base_url)

    # Make a simple reference implementation WSGI server
    server = simple_server.make_server("0.0.0.0", FLAGS.port,
                                       wsgi.WSGIHandler())
    while self.keep_running:
      server.handle_request()

  def Stop(self):
    self.keep_running = False
    # Force a request so the socket leaves accept()
    urllib.urlopen(self.base_url + "/quitmenow").read()
    self.join()


def MakeFixtures():
  # Make 10 clients
  for i in range(0, 10):
    test_lib.ClientFixture("C.%016X" % i)


class SeleniumTestLoader(unittest.TestLoader):
  """A test suite loader which searches for tests in all the plugins."""

  def loadTestsFromModule(self, _):
    """Just return all the tests as if they were in the same module."""
    tests = [self.loadTestsFromTestCase(x)
             for x in test_lib.GRRSeleniumTest.classes.values()]
    return self.suiteClass(tests)

  def loadTestsFromName(self, name, module=None):
    """Load the tests named."""
    parts = name.split(".")
    tests = self.loadTestsFromTestCase(
        test_lib.GRRSeleniumTest.classes[parts[0]])

    # Specifies the whole test suite.
    if len(parts) == 1:
      return self.suiteClass(tests)
    elif len(parts) == 2:
      return unittest.TestSuite([parts[0].__class__(parts[1])])


def main(argv):
  """Run the main test harness."""
  # Tests run the fake data store
  FLAGS.storage = "FakeDataStore"

  aff4.AFF4Init()

  # Make the fixtures
  MakeFixtures()


  setup_environ(settings)

  # Load up the tests after the environment has been configured.
  from grr.gui.plugins import tests

  # Start up a server in another thread
  trd = DjangoThread()
  trd.start()
  try:
    # Run the test suite
    if FLAGS.interactive:
      user_ns = dict()
      user_ns.update(globals())
      user_ns.update(locals())
      # Wait in the shell so selenium IDE can be used.
      Shell.IPShell(argv=[], user_ns=user_ns).mainloop()
    else:
      # Run the full test suite
      test_lib.GrrTestProgram(argv=argv, testLoader=SeleniumTestLoader())
  finally:
    # Kill the server thread
    trd.Stop()

if __name__ == "__main__":
  conf.StartMain(main)
