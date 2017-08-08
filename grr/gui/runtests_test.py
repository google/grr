#!/usr/bin/env python
"""This is a selenium test harness."""
import unittest

from grr.gui import gui_test_lib
# pylint: disable=unused-import
from grr.gui.selenium_tests import tests
# pylint: enable=unused-import
from grr.lib import flags
from grr.test_lib import test_lib


class SeleniumTestLoader(test_lib.GRRTestLoader):
  """A test suite loader which searches for tests in all the plugins."""
  base_class = gui_test_lib.GRRSeleniumTest


def main(argv):
  _ = argv
  suites = flags.FLAGS.tests or list(test_lib.GRRBaseTest.classes)
  unittest.TestProgram(
      argv=[argv[0]] + suites,
      testLoader=SeleniumTestLoader(),
      testRunner=unittest.TextTestRunner())


def DistEntry():
  """The main entry point for packages."""
  flags.StartMain(main)


if __name__ == "__main__":
  DistEntry()
