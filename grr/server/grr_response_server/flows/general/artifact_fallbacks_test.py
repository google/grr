#!/usr/bin/env python
"""Tests for grr.server.flows.general.artifact_fallbacks."""

from grr.lib import flags
from grr.lib.rdfvalues import paths as rdf_paths
from grr.server.grr_response_server import flow
from grr.server.grr_response_server.flows.general import artifact_fallbacks
from grr.test_lib import action_mocks
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib
from grr.test_lib import vfs_test_lib


class TestSystemRootSystemDriveFallbackFlow(flow_test_lib.FlowTestsBaseclass):

  def testSystemRootFallback(self):
    with vfs_test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.OS,
                                   vfs_test_lib.ClientVFSHandlerFixture):
      client_mock = action_mocks.ListDirectoryClientMock()

      session_id = flow_test_lib.TestFlowHelper(
          artifact_fallbacks.SystemRootSystemDriveFallbackFlow.__name__,
          client_mock,
          client_id=test_lib.TEST_CLIENT_ID,
          token=self.token,
          artifact_name="WindowsEnvironmentVariableSystemRoot")

      output_fd = flow.GRRFlow.ResultCollectionForFID(session_id)

      self.assertEqual(len(output_fd), 1)
      self.assertEqual(
          str(output_fd[0].registry_data.GetValue()), r"C:\WINDOWS")


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
