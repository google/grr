#!/usr/bin/env python
"""This is a selenium test harness."""
import os


import portpicker
from selenium import webdriver

import logging

from grr.gui import gui_test_lib
from grr.gui import wsgiapp_testlib
from grr.lib import flags
from grr.test_lib import test_lib


class SeleniumTestLoader(test_lib.GRRTestLoader):
  """A test suite loader which searches for tests in all the plugins."""
  base_class = gui_test_lib.GRRSeleniumTest


class SeleniumTestProgram(test_lib.GrrTestProgram):

  def SetupSelenium(self, port):
    gui_test_lib.GRRSeleniumTest.base_url = ("http://localhost:%s" % port)


    # pylint: disable=unreachable
    os.environ.pop("http_proxy", None)
    options = webdriver.ChromeOptions()
    gui_test_lib.GRRSeleniumTest.driver = webdriver.Chrome(
        chrome_options=options)

    # pylint: disable=unused-variable,g-import-not-at-top
    from grr.gui.plugins import tests
    # pylint: enable=unused-variable,g-import-not-at-top
    # pylint: enable=unreachable

  def TearDownSelenium(self):
    """Tear down the selenium session."""
    try:
      gui_test_lib.GRRSeleniumTest.driver.quit()
    except Exception as e:  # pylint: disable=broad-except
      logging.exception(e)

  def setUp(self):
    super(SeleniumTestProgram, self).setUp()
    # Select a free port
    port = portpicker.PickUnusedPort()
    logging.info("Picked free AdminUI port %d.", port)

    # Start up a server in another thread
    self.trd = wsgiapp_testlib.ServerThread(port)
    self.trd.StartAndWaitUntilServing()
    self.SetupSelenium(port)

  def tearDown(self):
    super(SeleniumTestProgram, self).tearDown()
    self.TearDownSelenium()


def main(argv):
  # Run the full test suite
  SeleniumTestProgram(argv=argv, testLoader=SeleniumTestLoader())


def DistEntry():
  """The main entry point for packages."""
  flags.StartMain(main)


if __name__ == "__main__":
  DistEntry()
