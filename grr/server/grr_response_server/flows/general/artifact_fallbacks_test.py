#!/usr/bin/env python
"""Tests for grr.server.flows.general.artifact_fallbacks."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib import flags
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_server.flows.general import artifact_fallbacks
from grr.test_lib import action_mocks
from grr.test_lib import db_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib
from grr.test_lib import vfs_test_lib


@db_test_lib.DualDBTest
class TestSystemRootSystemDriveFallbackFlow(flow_test_lib.FlowTestsBaseclass):

  def testSystemRootFallback(self):
    client_id = self.SetupClient(0)

    with vfs_test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.OS,
                                   vfs_test_lib.ClientVFSHandlerFixture):
      client_mock = action_mocks.ListDirectoryClientMock()

      session_id = flow_test_lib.TestFlowHelper(
          artifact_fallbacks.SystemRootSystemDriveFallbackFlow.__name__,
          client_mock,
          client_id=client_id,
          token=self.token,
          artifact_name="WindowsEnvironmentVariableSystemRoot")

      results = flow_test_lib.GetFlowResults(client_id, session_id)
      self.assertLen(results, 1)
      self.assertEqual(str(results[0].registry_data.GetValue()), r"C:\WINDOWS")


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
