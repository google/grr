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
import sys


from django.core.management import setup_environ


from grr.client import conf
from grr.client import conf as flags
import selenium


from grr.gui import runtests
from grr.gui import settings
from grr.lib import test_lib

flags.DEFINE_integer("selenium_port", 4444,
                    help="Port for local selenium server.")

FLAGS = flags.FLAGS


class SeleniumTestLoader(test_lib.GRRTestLoader):
  """A test suite loader which searches for tests in all the plugins."""
  base_class = test_lib.GRRSeleniumTest


class SeleniumTestProgram(test_lib.GrrTestProgram):

  def __init__(self, argv=None):
    self.SetupSelenium()
    try:
      super(SeleniumTestProgram, self).__init__(
          argv=argv, testLoader=SeleniumTestLoader())
    finally:
      self.TearDownSelenium()

  def SetupSelenium(self):
    # This is very expensive to start up - we make it a class attribute so it
    # can be shared with all the classes.
    test_lib.GRRSeleniumTest.selenium = selenium.selenium("localhost", FLAGS.selenium_port,
                                      "*chrome", "http://localhost:%s/" % FLAGS.port)

    test_lib.GRRSeleniumTest.selenium.start()

  def TearDownSelenium(self):
    """Tear down the selenium session."""
    test_lib.GRRSeleniumTest.selenium.stop()


def main(argv):
  # Tests run the fake data store
  FLAGS.storage = "FakeDataStore"


  setup_environ(settings)

  # Load up the tests after the environment has been configured.
  # pylint: disable=C6204,W0612
  from grr.gui.plugins import tests
  # pylint: enable=C6204

  # Start up a server in another thread
  trd = runtests.DjangoThread()
  trd.start()

  # Run the full test suite
  try:
    SeleniumTestProgram(argv=argv)
  finally:
    trd.Stop()

if __name__ == "__main__":
  conf.StartMain(main)
