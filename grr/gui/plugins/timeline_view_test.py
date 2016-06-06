#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Tests for the Timeline viewer flow."""



from grr.gui import runtests_test

from grr.lib import access_control
from grr.lib import action_mocks
from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import flags
from grr.lib import test_lib
from grr.lib.aff4_objects import aff4_grr
from grr.lib.flows.general import timelines
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import crypto as rdf_crypto
from grr.lib.rdfvalues import paths as rdf_paths


class TestTimelineView(test_lib.GRRSeleniumTest):
  """Test the timeline view."""

  def CreateTimelineFixture(self):
    """Creates a new timeline fixture we can play with."""
    # Create a client for testing
    client_id = rdf_client.ClientURN("C.0000000000000001")

    token = access_control.ACLToken(username="test", reason="fixture")

    fd = aff4.FACTORY.Create(client_id, aff4_grr.VFSGRRClient, token=token)
    cert = self.ClientCertFromPrivateKey(config_lib.CONFIG[
        "Client.private_key"])
    client_cert = rdf_crypto.RDFX509Cert(cert.as_pem())
    fd.Set(fd.Schema.CERT(client_cert))
    fd.Close()

    with test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.OS,
                               test_lib.ClientVFSHandlerFixture):
      client_mock = action_mocks.ActionMock("ListDirectory")
      output_path = "analysis/Timeline/MAC"

      for _ in test_lib.TestFlowHelper(
          "RecursiveListDirectory",
          client_mock,
          client_id=client_id,
          pathspec=rdf_paths.PathSpec(path="/",
                                      pathtype=rdf_paths.PathSpec.PathType.OS),
          token=token):
        pass

      # Now make a timeline
      for _ in test_lib.TestFlowHelper(timelines.MACTimes.__name__,
                                       client_mock,
                                       client_id=client_id,
                                       token=token,
                                       path="/",
                                       output=output_path):
        pass

  def setUp(self):
    test_lib.GRRSeleniumTest.setUp(self)

    # Create a new collection
    with self.ACLChecksDisabled():
      self.CreateTimelineFixture()
      self.RequestAndGrantClientApproval("C.0000000000000001")

  def testTimelineViewer(self):
    # Open the main page
    self.Open("/")

    self.Type("client_query", "C.0000000000000001")
    self.Click("client_query_submit")

    self.WaitUntilEqual(u"C.0000000000000001", self.GetText,
                        "css=span[type=subject]")

    # Choose client 1
    self.Click("css=td:contains('0001')")

    # Go to Browse VFS
    self.Click("css=a:contains('Browse Virtual Filesystem')")

    # Navigate to the analysis directory
    self.Click("css=#_analysis i.jstree-icon")

    self.Click("link=Timeline")

    self.Click("css=span[type=subject]:contains(\"MAC\")")

    self.WaitUntil(self.IsElementPresent, "css=td:contains(\"TIMELINE\")")
    self.assertIn("View details", self.GetText("css=td div.default_view a"))

    self.Click("css=a:contains(\"View details\")")

    self.WaitUntil(self.IsElementPresent, "container_query")

    self.Type("css=input#container_query",
              "subject contains bash and timestamp > 2010")

    # Use the hidden submit button to issue the query. Ordinarily users have to
    # press enter here as they do not see the submit button. But pressing enter
    # does not work with chrome.
    self.Click("css=#toolbar_main form[name=query_form] button[type=submit]")

    self.WaitUntilContains("2011-03-07 12:50:20", self.GetText,
                           "css=tbody tr:first")

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
