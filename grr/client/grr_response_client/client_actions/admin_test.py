#!/usr/bin/env python
"""Tests client actions related to administrating the client."""

import io
import os
import tempfile
from unittest import mock

from absl import app
from absl.testing import absltest

from grr_response_client.client_actions import admin
from grr_response_client.unprivileged import sandbox
from grr_response_core import config
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr.test_lib import client_test_lib
from grr.test_lib import test_lib
from grr.test_lib import worker_mocks


class ConfigActionTest(client_test_lib.EmptyActionTest):
  """Tests the client actions UpdateConfiguration and GetConfiguration."""

  def setUp(self):
    super().setUp()
    # These tests change the config so we preserve state.
    config_stubber = test_lib.PreserveConfig()
    config_stubber.Start()
    self.addCleanup(config_stubber.Stop)

  def testUpdateConfiguration(self):
    """Test that we can update the config."""
    # A unique name on the filesystem for the writeback.
    self.config_file = os.path.join(self.temp_dir, "ConfigActionTest.yaml")

    # In a real client, the writeback location should be set to something real,
    # but for this test we make it the same as the config file..
    config.CONFIG.SetWriteBack(self.config_file)

    # Make sure the file is gone
    self.assertRaises(IOError, open, self.config_file)

    location = ["http://www.example1.com/", "http://www.example2.com/"]
    request = rdf_protodict.Dict()
    request["Client.server_urls"] = location
    request["Client.foreman_check_frequency"] = 3600

    result = self.RunAction(admin.UpdateConfiguration, request)

    self.assertEqual(result, [])
    self.assertEqual(config.CONFIG["Client.foreman_check_frequency"], 3600)

    # Test the config file got written.
    with io.open(self.config_file, "r") as filedesc:
      data = filedesc.read()

    server_urls = """
Client.server_urls:
- http://www.example1.com/
- http://www.example2.com/
"""
    self.assertIn(server_urls, data)

  def testOnlyUpdatableFieldsAreUpdated(self):
    with test_lib.ConfigOverrider({
        "Client.server_urls": ["http://something.com/"],
        "Client.server_serial_number": 1,
    }):

      location = ["http://www.example.com"]
      request = rdf_protodict.Dict()
      request["Client.server_urls"] = location
      request["Client.server_serial_number"] = 10

      with self.assertRaises(ValueError):
        self.RunAction(admin.UpdateConfiguration, request)

      # Nothing was updated.
      self.assertEqual(
          config.CONFIG["Client.server_urls"], ["http://something.com/"]
      )
      self.assertEqual(config.CONFIG["Client.server_serial_number"], 1)

  def testGetConfig(self):
    """Check GetConfig client action works."""
    # Use UpdateConfig to generate a config.
    location = ["http://example.com/"]
    request = rdf_protodict.Dict()
    request["Client.server_urls"] = location
    request["Client.foreman_check_frequency"] = 3600

    self.RunAction(admin.UpdateConfiguration, request)
    # Check that our GetConfig actually gets the real data.
    self.RunAction(admin.GetConfiguration)

    self.assertEqual(config.CONFIG["Client.foreman_check_frequency"], 3600)
    self.assertEqual(config.CONFIG["Client.server_urls"], location)


class GetClientInformationTest(absltest.TestCase):

  def testTimelineBtimeSupport(self):
    client_info = admin.GetClientInformation()

    # We cannot assume anything about the support being there or not, so we just
    # check that some information is set. This should be enough to guarantee
    # line coverage.
    self.assertTrue(client_info.HasField("timeline_btime_support"))

  def testSandboxSupport(self):
    with mock.patch.object(sandbox, "IsSandboxInitialized", return_value=True):
      client_info = admin.GetClientInformation()
      self.assertTrue(client_info.sandbox_support)
    with mock.patch.object(sandbox, "IsSandboxInitialized", return_value=False):
      client_info = admin.GetClientInformation()
      self.assertFalse(client_info.sandbox_support)


class SendStartupInfoTest(client_test_lib.EmptyActionTest):

  def _RunAction(self):
    fake_worker = worker_mocks.FakeClientWorker()
    self.RunAction(admin.SendStartupInfo, grr_worker=fake_worker)
    return [m.payload for m in fake_worker.responses]

  def testDoesNotSendInterrogateRequestWhenConfigOptionNotSet(self):
    results = self._RunAction()

    self.assertLen(results, 1)
    self.assertFalse(results[0].interrogate_requested)

  def testDoesNotSendInterrogateRequestWhenTriggerFileIsMissing(self):
    with test_lib.ConfigOverrider(
        {"Client.interrogate_trigger_path": "/none/existingpath"}
    ):
      results = self._RunAction()

    self.assertLen(results, 1)
    self.assertFalse(results[0].interrogate_requested)

  def testSendsInterrogateRequestWhenTriggerFileIsPresent(self):
    with tempfile.NamedTemporaryFile(delete=False) as fd:
      trigger_path = fd.name

    with test_lib.ConfigOverrider(
        {"Client.interrogate_trigger_path": trigger_path}
    ):
      results = self._RunAction()

    # Check that the trigger file got removed.
    self.assertFalse(os.path.exists(trigger_path))

    self.assertLen(results, 1)
    self.assertTrue(results[0].interrogate_requested)

  def testInterrogateIsTriggeredOnlyOnceForOneTriggerFile(self):
    with tempfile.NamedTemporaryFile(delete=False) as fd:
      trigger_path = fd.name

    with test_lib.ConfigOverrider(
        {"Client.interrogate_trigger_path": trigger_path}
    ):
      results = self._RunAction()

      self.assertLen(results, 1)
      self.assertTrue(results[0].interrogate_requested)

      results = self._RunAction()

      self.assertLen(results, 1)
      self.assertFalse(results[0].interrogate_requested)

  @mock.patch.object(os, "remove", side_effect=OSError("some error"))
  def testInterrogateNotRequestedIfTriggerFileCanNotBeRemoved(self, _):
    with tempfile.NamedTemporaryFile() as fd:
      trigger_path = fd.name

    with test_lib.ConfigOverrider(
        {"Client.interrogate_trigger_path": trigger_path}
    ):
      results = self._RunAction()

    self.assertLen(results, 1)
    self.assertFalse(results[0].interrogate_requested)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
