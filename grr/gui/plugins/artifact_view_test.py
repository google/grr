#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Test the artifact rendering interface."""


import os

from grr.gui import runtests_test
from grr.lib import artifact
from grr.lib import artifact_registry
from grr.lib import config_lib
from grr.lib import flags
from grr.lib import parsers
from grr.lib import test_lib


class TestCmdProcessor(parsers.CommandParser):

  output_types = ["SoftwarePackage"]
  supported_artifacts = ["TestCmdArtifact"]


class TestArtifactRender(test_lib.GRRSeleniumTest):
  """Test the Cron view GUI."""

  def setUp(self):
    super(TestArtifactRender, self).setUp()
    artifact_registry.REGISTRY.ClearRegistry()
    test_artifacts_file = os.path.join(config_lib.CONFIG["Test.data_dir"],
                                       "artifacts", "test_artifacts.json")
    artifact_registry.REGISTRY.AddFileSource(test_artifacts_file)

  def tearDown(self):
    super(TestArtifactRender, self).tearDown()
    artifact.ArtifactLoader().RunOnce()

  def testArtifactRendering(self):
    self.Open("/")
    with self.ACLChecksDisabled():
      self.RequestAndGrantClientApproval("C.0000000000000001")
    self.Open("/")

    self.Type("client_query", "C.0000000000000001")
    self.Click("client_query_submit")

    self.WaitUntilEqual(u"C.0000000000000001", self.GetText,
                        "css=span[type=subject]")
    # Choose client 1
    self.Click("css=td:contains('0001')")

    # First screen should be the Host Information already.
    self.WaitUntil(self.IsTextPresent, "HostC.0000000000000001")
    self.Click("css=a[grrtarget='client.launchFlows']")
    self.Click("css=#_Collectors")

    self.assertEqual("ArtifactCollectorFlow",
                     self.GetText("link=ArtifactCollectorFlow"))
    self.Click("link=ArtifactCollectorFlow")
    self.WaitUntil(self.IsTextPresent, "Artifact list")

    self.Click("css=grr-artifacts-list-form button:contains('All Platforms')")
    self.Click("css=grr-artifacts-list-form li:contains('Linux')")

    # Check search works. Note that test artifacts names are used (see
    # test_data/artifacts/test_artifacts.json for details.
    self.WaitUntil(self.IsTextPresent, "TestCmdArtifact")
    self.WaitUntil(self.IsTextPresent, "TestFilesArtifact")

    self.Type("css=grr-artifacts-list-form input[type=text]", u"Cmd")
    self.WaitUntil(self.IsTextPresent, "TestCmdArtifact")
    self.WaitUntilNot(self.IsTextPresent, "TestFilesArtifact")

    # Check we can add to the list.
    self.Click("css=grr-artifacts-list-form tr:contains('TestCmdArtifact')")
    self.Click("css=grr-artifacts-list-form button:contains('Add')")
    # Selected artifacts should be highlighted in bold.
    self.WaitUntil(self.IsElementPresent, "css=grr-artifacts-list-form "
                   "strong:contains('TestCmdArtifact')")

    # Check the artifact description loaded.
    self.WaitUntil(self.IsTextPresent, "Test command artifact for dpkg.")
    self.WaitUntil(self.IsTextPresent, "TestCmdProcessor")


def main(argv):
  # Run the full test suite
  runtests_test.SeleniumTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)
