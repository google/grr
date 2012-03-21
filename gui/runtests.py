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

"""This is a selenium test harness used interactively with Selenium IDE."""
import socket
import sys
import threading
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
from grr.lib import data_store

from grr.lib import fake_data_store
from grr.lib import flow
from grr.lib import registry
from grr.lib import test_lib
from grr.lib.flows import general

flags.DEFINE_integer("port", 8000,
                     "port to listen on for selenium tests.")

FLAGS = flags.FLAGS


class DjangoThread(threading.Thread):
  """A class to run the wsgi server in another thread."""

  keep_running = True

  def __init__(self, **kwargs):
    super(DjangoThread, self).__init__(**kwargs)
    self.base_url = "http://%s:%d" % (socket.getfqdn(), FLAGS.port)

  def run(self):
    """Run the django server in a thread."""
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


class RunTestsInit(aff4.AFF4InitHook):
  altitude = aff4.AFF4InitHook.altitude + 10

  def __init__(self):
    # Install the mock security manager so we can trap errors in interactive
    # mode.
    data_store.DB.security_manager = test_lib.MockSecurityManager()
    token = data_store.ACLToken("Test", "Make fixtures.")
    # Make 10 clients
    for i in range(0, 10):
      test_lib.ClientFixture("C.%016X" % i, token=token)


def main(_):
  """Run the main test harness."""
  # Tests run the fake data store
  FLAGS.storage = "FakeDataStore"


  setup_environ(settings)

  # Load up the tests after the environment has been configured.
  from grr.gui.plugins import tests

  # Start up a server in another thread
  trd = DjangoThread()
  trd.start()
  try:
    user_ns = dict()
    user_ns.update(globals())
    user_ns.update(locals())

    registry.Init()

    # Wait in the shell so selenium IDE can be used.
    Shell.IPShell(argv=[], user_ns=user_ns).mainloop()
  finally:
    # Kill the server thread
    trd.Stop()

if __name__ == "__main__":
  conf.StartMain(main)
