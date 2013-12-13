#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Test the artifact rendering interface."""


import os

from grr.gui import runtests_test
from grr.lib import config_lib
from grr.lib import flags
from grr.lib import test_lib


class TestArtifactManagementRender(test_lib.GRRSeleniumTest):
  """Test the Cron view GUI."""

  def testArtifactRendering(self):
    self.Open("/")

    self.Click("css=a[grrtarget=ArtifactManagerView]")

    self.WaitUntil(self.IsTextPresent, "Artifact Details")

    self.Click("css=button[id$=_upload]")
    self.WaitUntil(self.IsTextPresent, "Upload File")

    json_file = os.path.realpath(os.path.join(
        config_lib.CONFIG["Test.data_dir"], "test_artifact.json"))

    # Can't use self.Type here as it isn't a standard input box.
    element = self.WaitUntil(self.GetVisibleElement, "css=input[id$=_file]")
    element.send_keys(json_file)

    self.Click("css=button[id$=_upload_button]")
    self.WaitUntil(self.IsTextPresent, "Success: File uploaded")
    self.Click("css=button[id^=upload_artifact_close_btn_]")

    # Refresh artifact list.
    self.Click("css=a[grrtarget=ArtifactManagerView]")
    self.WaitUntil(self.IsTextPresent, "Artifact Details")
    self.WaitUntil(self.IsTextPresent, "TestDrivers")


def main(argv):
  # Run the full test suite
  runtests_test.SeleniumTestProgram(argv=argv)

if __name__ == "__main__":
  flags.StartMain(main)
