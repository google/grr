#!/usr/bin/env python
"""Tests client actions related to administrating the client."""

import os
import tempfile
from unittest import mock

from absl import app
from absl.testing import absltest

from grr_response_client.client_actions import admin
from grr_response_client.unprivileged import sandbox
from grr.test_lib import client_test_lib
from grr.test_lib import test_lib
from grr.test_lib import worker_mocks


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
