#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Test the artifact rendering interface."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import os


from grr_response_core import config
from grr_response_core.lib import flags
from grr_response_server import artifact
from grr_response_server import artifact_registry
from grr_response_server.gui import gui_test_lib
from grr.test_lib import db_test_lib
from grr.test_lib import test_lib


@db_test_lib.DualDBTest
class TestArtifactManagementRender(gui_test_lib.GRRSeleniumTest):
  """Test the Cron view GUI."""

  def setUp(self):
    super(TestArtifactManagementRender, self).setUp()

    self.json_file = os.path.realpath(
        os.path.join(config.CONFIG["Test.data_dir"], "artifacts",
                     "test_artifact.json"))

  def testArtifactUpload(self):
    self.Open("/#main=ArtifactManagerView")

    self.WaitUntil(self.IsTextPresent, "Artifact Details")

    self.Click("css=grr-artifact-manager-view button[name=UploadArtifact]")
    self.WaitUntil(self.IsTextPresent, "Upload Artifact")

    # Can't use self.Type here as it isn't a standard input box.
    element = self.WaitUntil(self.GetVisibleElement,
                             "css=grr-upload-artifact-dialog input[type=file]")
    element.send_keys(self.json_file)

    self.Click("css=grr-upload-artifact-dialog button[name=Proceed]")
    self.WaitUntil(self.IsTextPresent, "Artifact was successfully uploaded.")
    self.Click("css=grr-upload-artifact-dialog button[name=Close]")

    # Check that the list is refreshed.
    self.WaitUntil(self.IsTextPresent, "TestDrivers")

  def testSystemArtifactOverwriteIsForbidden(self):
    # Load the artifact directly from the file.
    artifact_registry.REGISTRY.AddFileSource(self.json_file)

    self.Open("/#main=ArtifactManagerView")

    self.WaitUntil(self.IsTextPresent, "Artifact Details")

    # Now, we should get an error if we try to overwrite the existing artifact.
    self.Click("css=grr-artifact-manager-view button[name=UploadArtifact]")
    self.WaitUntil(self.IsTextPresent, "Upload Artifact")

    # Can't use self.Type here as it isn't a standard input box.
    element = self.WaitUntil(self.GetVisibleElement,
                             "css=grr-upload-artifact-dialog input[type=file]")
    element.send_keys(self.json_file)

    # TODO(user): at the moment trying to overwrite a system artifact
    # leads to HTTP 500 (Server error). This should be changed to
    # HTTP 403 (Forbidden).
    with self.DisableHttpErrorChecks():
      self.Click("css=grr-upload-artifact-dialog button[name=Proceed]")
      self.WaitUntil(self.IsTextPresent,
                     "TestDrivers: system artifact cannot be overwritten")

  def testArtifactAvailableImmediatelyAfterUpload(self):
    client_id = self.SetupClient(0).Basename()
    self.RequestAndGrantClientApproval(client_id)

    # Test that we have no TestDrivers.
    self.Open("/#/clients/%s/launch-flow" % client_id)
    self.Click("css=#_Collectors a")
    self.Click("link=ArtifactCollectorFlow")
    self.WaitUntil(self.IsTextPresent, "Artifact list")
    self.WaitUntilNot(self.IsTextPresent, "Loading artifacts...")
    self.WaitUntilNot(self.IsTextPresent, "TestDrivers")

    # Upload the artifact.
    self.Click("css=a[grrtarget=artifacts]")
    self.Click("css=grr-artifact-manager-view button[name=UploadArtifact]")
    element = self.WaitUntil(self.GetVisibleElement,
                             "css=grr-upload-artifact-dialog input[type=file]")
    element.send_keys(self.json_file)
    self.Click("css=grr-upload-artifact-dialog button[name=Proceed]")
    self.WaitUntil(self.IsTextPresent, "Artifact was successfully uploaded.")
    self.Click("css=grr-upload-artifact-dialog button[name=Close]")

    # Test that now we can choose TestDrivers in the form.
    self.Click("css=a[grrtarget='client.launchFlows']")
    self.Click("css=#_Collectors a")
    self.Click("link=ArtifactCollectorFlow")
    self.WaitUntil(self.IsTextPresent, "TestDrivers")

  def testArtifactDeletion(self):
    with open(self.json_file, "rb") as fd:
      artifact.UploadArtifactYamlFile(fd.read())

    self.Open("/#main=ArtifactManagerView")

    # Check that test artifact is displayed.
    self.WaitUntil(self.IsTextPresent, "TestDrivers")

    # Click on TestDrivers checkbox and click Delete.
    self.Click("css=grr-artifact-manager-view tr:contains('TestDrivers') "
               "input[type=checkbox]")
    self.Click("css=grr-artifact-manager-view button[name=DeleteArtifact]")

    # Check that dialog mentions TestDrivers and click on Proceed, then Close.
    self.WaitUntil(self.IsTextPresent, "Delete Selected Artifacts")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-delete-artifacts-dialog:contains('TestDrivers')")
    self.Click("css=grr-delete-artifacts-dialog button[name=Proceed]")
    self.WaitUntil(self.IsTextPresent, "Artifacts were deleted successfully.")
    self.Click("css=grr-delete-artifacts-dialog button[name=Close]")

    # Check that artifact is indeed deleted.
    self.WaitUntilNot(self.IsTextPresent, "Delete Selected Artifacts")
    self.WaitUntilNot(self.IsTextPresent, "Loading...")
    self.WaitUntilNot(self.IsTextPresent, "TestDrivers")

  def testArtifactRemovedFromFormsImmediatelyAfterDeletion(self):
    with open(self.json_file, "rb") as fd:
      artifact.UploadArtifactYamlFile(fd.read())

    client_id = self.SetupClient(0).Basename()
    self.RequestAndGrantClientApproval(client_id)

    # Test that we have TestDrivers available.
    self.Open("/#/clients/%s/launch-flow" % client_id)
    self.Click("css=#_Collectors a")
    self.Click("link=ArtifactCollectorFlow")
    self.WaitUntil(self.IsTextPresent, "TestDrivers")

    # Upload the artifact.
    self.Click("css=a[grrtarget=artifacts]")
    self.Click("css=grr-artifact-manager-view tr:contains('TestDrivers') "
               "input[type=checkbox]")
    self.Click("css=grr-artifact-manager-view button[name=DeleteArtifact]")
    self.Click("css=grr-delete-artifacts-dialog button[name=Proceed]")
    self.WaitUntil(self.IsTextPresent, "Artifacts were deleted successfully.")
    self.Click("css=grr-delete-artifacts-dialog button[name=Close]")

    # Test now we can choose TestDrivers in the form.
    self.Click("css=a[grrtarget='client.launchFlows']")
    self.Click("css=#_Collectors a")
    self.Click("link=ArtifactCollectorFlow")
    self.WaitUntil(self.IsTextPresent, "Artifact list")
    self.WaitUntilNot(self.IsTextPresent, "Loading artifacts...")
    self.WaitUntilNot(self.IsTextPresent, "TestDrivers")


if __name__ == "__main__":
  flags.StartMain(test_lib.main)
