#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

"""Test the Rekall collection viewer interface."""


from grr.client.client_actions import grr_rekall_test
from grr.gui import runtests_test
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import test_lib


class TestRekallViewer(test_lib.GRRSeleniumTest,
                       grr_rekall_test.RekallTestSuite):
  """Test the fileview interface."""

  def setUp(self):
    super(TestRekallViewer, self).setUp()

    self.UninstallACLChecks()

    request = rdfvalue.RekallRequest()
    request.plugins = [
        # Only use these methods for listing processes.
        rdfvalue.PluginRequest(
            plugin="pslist", args=dict(
                method=["PsActiveProcessHead", "CSRSS"]
            )),
        rdfvalue.PluginRequest(plugin="modules")]

    self.LaunchRekallPlugin(request)

  def testRekallView(self):
    self.Open("/")

    self.Type("client_query", "Host-0")
    self.Click("client_query_submit")

    self.WaitUntilEqual(u"C.1000000000000000",
                        self.GetText, "css=span[type=subject]")

    # Choose client 1
    self.Click("css=td:contains('1000')")

    # Go to Browse VFS
    self.Click("css=a:contains('Browse Virtual Filesystem')")

    self.Click("css=#_analysis")
    self.Click("css=tr:contains(\"memory\")")

    self.WaitUntil(self.IsTextPresent, "Results")
    self.Click("css=#Results")

    self.WaitUntilContains("pslist", self.GetText,
                           "css=div#main_rightBottomPane")

    self.WaitUntilContains("DumpIt.exe", self.GetText,
                           "css=div#main_rightBottomPane")

    self.WaitUntilContains("Wow64", self.GetText,
                           "css=div#main_rightBottomPane")


def main(argv):
  # Run the full test suite
  runtests_test.SeleniumTestProgram(argv=argv)

if __name__ == "__main__":
  flags.StartMain(main)
