#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

# Copyright 2011 Google Inc. All Rights Reserved.
"""Tests for the Timeline viewer flow."""



from grr.client import vfs

from grr.gui import runtests_test

from grr.lib import access_control
from grr.lib import action_mocks
from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import test_lib


class TestTimelineView(test_lib.GRRSeleniumTest):
  """Test the timeline view."""

  def CreateTimelineFixture(self):
    """Creates a new timeline fixture we can play with."""
    # Create a client for testing
    client_id = rdfvalue.ClientURN("C.0000000000000001")

    token = access_control.ACLToken(username="test", reason="fixture")

    fd = aff4.FACTORY.Create(client_id, "VFSGRRClient", token=token)
    cert = self.ClientCertFromPrivateKey(
        config_lib.CONFIG["Client.private_key"])
    client_cert = rdfvalue.RDFX509Cert(cert.as_pem())
    fd.Set(fd.Schema.CERT(client_cert))
    fd.Close()

    # Install the mock
    vfs.VFS_HANDLERS[
        rdfvalue.PathSpec.PathType.OS] = test_lib.ClientVFSHandlerFixture
    client_mock = action_mocks.ActionMock("ListDirectory")
    output_path = "analysis/Timeline/MAC"

    for _ in test_lib.TestFlowHelper(
        "RecursiveListDirectory", client_mock, client_id=client_id,
        pathspec=rdfvalue.PathSpec(
            path="/", pathtype=rdfvalue.PathSpec.PathType.OS),
        token=token):
      pass

    # Now make a timeline
    for _ in test_lib.TestFlowHelper(
        "MACTimes", client_mock, client_id=client_id, token=token,
        path="/", output=output_path):
      pass

  def setUp(self):
    test_lib.GRRSeleniumTest.setUp(self)

    # Create a new collection
    with self.ACLChecksDisabled():
      self.CreateTimelineFixture()
      self.GrantClientApproval("C.0000000000000001")

  def testTimelineViewer(self):
    # Open the main page
    self.Open("/")

    self.Type("client_query", "0001")
    self.Click("client_query_submit")

    self.WaitUntilEqual(u"C.0000000000000001",
                        self.GetText, "css=span[type=subject]")

    # Choose client 1
    self.Click("css=td:contains('0001')")

    # Go to Browse VFS
    self.Click("css=a:contains('Browse Virtual Filesystem')")

    # Navigate to the analysis directory
    self.Click("css=#_analysis ins.jstree-icon")

    self.Click("link=Timeline")

    self.Click("css=span[type=subject]:contains(\"MAC\")")

    self.WaitUntil(self.IsElementPresent, "css=td:contains(\"TIMELINE\")")
    self.assert_("View details" in self.GetText("css=td div.default_view a"))

    self.Click("css=a:contains(\"View details\")")

    self.WaitUntil(self.IsElementPresent, "container_query")

    self.Type("css=input#container_query",
              "subject contains bash and timestamp > 2010")

    # Use the hidden submit button to issue the query. Ordinarily users have to
    # press enter here as they do not see the submit button. But pressing enter
    # does not work with chrome.
    self.Click("css=#toolbar_main form[name=query_form] button[type=submit]")

    self.WaitUntilContains("2011-03-07 12:50:20",
                           self.GetText, "css=tbody tr:first")

    self.Click("css=tbody tr:first td")

    self.WaitUntilContains("2011-03-07 12:50:20", self.GetText,
                           "css=.tab-content h3")

    # Check that the embedded stat proto is properly presented
    self.assertTrue("2011-03-07 12:50:20" in self.GetText(
        "css=td.proto_value tr:contains('St atime') td.proto_value"))


def main(argv):
  # Run the full test suite
  runtests_test.SeleniumTestProgram(argv=argv)

if __name__ == "__main__":
  flags.StartMain(main)
