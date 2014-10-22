#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Test the artifact rendering interface."""


from grr.gui import runtests_test
from grr.lib import artifact_test
from grr.lib import flags
from grr.lib import test_lib


class TestArtifactRender(test_lib.GRRSeleniumTest):
  """Test the Cron view GUI."""

  def setUp(self):
    super(TestArtifactRender, self).setUp()
    artifact_test.ArtifactTest.LoadTestArtifacts()

  def testArtifactRendering(self):
    self.Open("/")
    with self.ACLChecksDisabled():
      self.GrantClientApproval("C.0000000000000001")
    self.Open("/")

    self.Type("client_query", "0001")
    self.Click("client_query_submit")

    self.WaitUntilEqual(u"C.0000000000000001",
                        self.GetText, "css=span[type=subject]")
    # Choose client 1
    self.Click("css=td:contains('0001')")

    # First screen should be the Host Information already.
    self.WaitUntil(self.IsTextPresent, "VFSGRRClient")
    self.Click("css=a[grrtarget=LaunchFlows]")
    self.Click("css=#_Collectors")

    self.assertEqual("ArtifactCollectorFlow",
                     self.GetText("link=ArtifactCollectorFlow"))
    self.Click("link=ArtifactCollectorFlow")
    self.WaitUntil(self.IsTextPresent, "Artifact list")

    self.Select("css=select[id$=_os_filter]", "Linux")

    # Check search works.
    self.Type("css=input[id$=_search]", u"Lin")
    self.WaitUntil(self.IsTextPresent, "LinuxPasswd")

    # Check we can add to the list.
    self.Click("css=option[value=LinuxPasswd]")
    self.Click("css=a[id$=_artifact_add]")

    self.Select("css=#args-artifact_list", "LinuxPasswd")
    self.Click("css=option[value=LinuxPasswd]")

    # Force selection due to selenium not propagating change correctly.
    self.driver.execute_script("return $('#args-artifact_list').change()")

    # Check the artifact description loaded.
    self.WaitUntil(self.IsTextPresent, "Linux passwd file.")
    self.WaitUntil(self.IsTextPresent, "PasswdParser")


def main(argv):
  # Run the full test suite
  runtests_test.SeleniumTestProgram(argv=argv)

if __name__ == "__main__":
  flags.StartMain(main)
