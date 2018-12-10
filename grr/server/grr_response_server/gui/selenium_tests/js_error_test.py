#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Test Selenium tests JS errors detection logic."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from grr_response_core.lib import flags
from grr_response_server.gui import gui_test_lib
from grr.test_lib import test_lib


class JavascriptErrorTest(gui_test_lib.GRRSeleniumTest):
  """Tests that Javascript errors are caught in Selenium tests."""

  def testJavascriptErrorTriggersPythonExcpetion(self):
    self.Open("/")

    # Erase global Angular object.
    # Things are guaranteed to stop working correctly after this.
    self.GetJavaScriptValue("window.angular = undefined;")

    self.Click("client_query_submit")
    with self.assertRaisesRegexp(self.failureException,
                                 "Javascript error encountered"):
      self.WaitUntil(self.IsElementPresent, "css=grr-clients-list")

    # The page has some tickers running that also use Angular so there
    # is a race that they can cause more js errors after the test has
    # already finished. By navigating to the main page, we make sure
    # the Angular object is valid again which means no more errors and
    # also clear the list of recorded errors in case there have been
    # any in the meantime.
    self.Open("/")


if __name__ == "__main__":
  flags.StartMain(test_lib.main)
