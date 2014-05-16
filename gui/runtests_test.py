#!/usr/bin/env python
"""This is a selenium test harness."""
import os


from selenium import webdriver

import logging

from grr.gui import runtests
from grr.lib import config_lib
from grr.lib import flags
from grr.lib import test_lib


class SeleniumTestLoader(test_lib.GRRTestLoader):
  """A test suite loader which searches for tests in all the plugins."""
  base_class = test_lib.GRRSeleniumTest


class SeleniumTestProgram(test_lib.GrrTestProgram):

  def __init__(self, argv=None):
    super(SeleniumTestProgram, self).__init__(
        argv=argv, testLoader=SeleniumTestLoader())

  def SetupSelenium(self):
    os.environ.pop("http_proxy", None)

    # This is very expensive to start up - we make it a class attribute so it
    # can be shared with all the classes.
    test_lib.GRRSeleniumTest.base_url = (
        "http://localhost:%s" % config_lib.CONFIG["AdminUI.port"])

    options = webdriver.ChromeOptions()
    test_lib.GRRSeleniumTest.driver = webdriver.Chrome(chrome_options=options)


  def TearDownSelenium(self):
    """Tear down the selenium session."""
    try:
      test_lib.GRRSeleniumTest.driver.quit()
    except Exception as e:  # pylint: disable=broad-except
      logging.exception(e)

  def setUp(self):

    # Start up a server in another thread
    self.trd = runtests.DjangoThread()
    self.trd.start()
    self.SetupSelenium()

  def tearDown(self):
    self.TearDownSelenium()


def main(argv):
  # Run the full test suite
  SeleniumTestProgram(argv=argv)

if __name__ == "__main__":
  flags.StartMain(main)
