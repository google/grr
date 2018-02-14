#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Test Selenium tests JS errors detection logic."""

import unittest
from grr.gui import gui_test_lib
from grr.lib import flags


class JavascriptErrorTest(gui_test_lib.GRRSeleniumTest):
  """Tests that Javascript errors are caught in Selenium tests."""

  def testJavascriptErrorTriggersPythonExcpetion(self):
    self.Open("/")

    # Erase global Angular object.
    # Things are guaranteed to stop working correctly after this.
    self.GetJavaScriptValue("window.angular = undefined;")

    with self.assertRaisesRegexp(self.failureException,
                                 "Javascript error encountered"):
      self.Click("client_query_submit")
      self.WaitUntil(self.IsElementPresent, "css=grr-clients-list")


def main(argv):
  del argv  # Unused.
  # Run the full test suite
  unittest.main()


if __name__ == "__main__":
  flags.StartMain(main)
