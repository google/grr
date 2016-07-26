#!/usr/bin/env python
"""Tests for grr.lib.flows.general.artifact_fallbacks."""

from grr.lib import action_mocks
from grr.lib import aff4
from grr.lib import flags
from grr.lib import flow_runner
from grr.lib import test_lib
# pylint: disable=unused-import
from grr.lib.flows.general import artifact_fallbacks as _
# pylint: enable=unused-import
from grr.lib.rdfvalues import paths as rdf_paths


class TestSystemRootSystemDriveFallbackFlow(test_lib.FlowTestsBaseclass):

  def testSystemRootFallback(self):
    with test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.OS,
                               test_lib.ClientVFSHandlerFixture):
      client_mock = action_mocks.ActionMock("ListDirectory", "StatFile")

      for s in test_lib.TestFlowHelper(
          "SystemRootSystemDriveFallbackFlow",
          client_mock,
          client_id=self.client_id,
          token=self.token,
          artifact_name="SystemRoot"):
        session_id = s

      output_fd = aff4.FACTORY.Open(
          session_id.Add(flow_runner.RESULTS_SUFFIX), token=self.token)

      self.assertEqual(len(output_fd), 1)
      self.assertEqual(
          str(output_fd[0].registry_data.GetValue()), r"C:\WINDOWS")


def main(argv):
  # Run the full test suite
  test_lib.GrrTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)
