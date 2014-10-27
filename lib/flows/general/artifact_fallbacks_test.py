#!/usr/bin/env python
"""Tests for grr.lib.flows.general.artifact_fallbacks."""

from grr.client import vfs
from grr.lib import action_mocks
from grr.lib import aff4
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import test_lib


class TestSystemRootSystemDriveFallbackFlow(test_lib.FlowTestsBaseclass):

  def testSystemRootFallback(self):
    vfs.VFS_HANDLERS[
        rdfvalue.PathSpec.PathType.OS] = test_lib.ClientVFSHandlerFixture
    client_mock = action_mocks.ActionMock("ListDirectory", "StatFile")

    for _ in test_lib.TestFlowHelper(
        "SystemRootSystemDriveFallbackFlow", client_mock,
        client_id=self.client_id, token=self.token, artifact_name="SystemRoot",
        output="systemroot"):
      pass

    output_fd = aff4.FACTORY.Open(self.client_id.Add("systemroot"),
                                  token=self.token)

    self.assertEqual(len(output_fd), 1)
    self.assertEqual(str(output_fd[0].registry_data.GetValue()), r"C:\WINDOWS")


class FlowTestLoader(test_lib.GRRTestLoader):
  base_class = TestSystemRootSystemDriveFallbackFlow


def main(argv):
  # Run the full test suite
  test_lib.GrrTestProgram(argv=argv, testLoader=FlowTestLoader())

if __name__ == "__main__":
  flags.StartMain(main)
