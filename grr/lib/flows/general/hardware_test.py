#!/usr/bin/env python
"""Tests for low-level flows."""

from grr.client.client_actions import tempfiles
from grr.client.components.chipsec_support import chipsec_types
from grr.lib import action_mocks
from grr.lib import aff4
from grr.lib import flags
from grr.lib import flow
from grr.lib import test_lib
from grr.lib.aff4_objects import collects
# pylint: disable=unused-import
from grr.lib.flows.general import hardware
# pylint: enable=unused-import
from grr.lib.rdfvalues import paths as rdf_paths


class DumpFlashImageMock(action_mocks.ActionMock):
  """Mock the flash dumping on the client side."""

  def DumpFlashImage(self, args):
    flash_fd, flash_path = tempfiles.CreateGRRTempFileVFS()
    flash_fd.write("\xff" * 1024)
    flash_fd.close()
    logs = ["test"] if args.log_level else []
    response = chipsec_types.DumpFlashImageResponse(path=flash_path, logs=logs)
    return [response]


class UnknownChipsetDumpMock(action_mocks.ActionMock):

  def DumpFlashImage(self, args):
    logs = ["Unknown chipset"]
    response = chipsec_types.DumpFlashImageResponse(logs=logs)
    return [response]


class FailDumpMock(action_mocks.ActionMock):

  def DumpFlashImage(self, args):
    raise IOError("Unexpected error")


class TestDumpFlashImage(test_lib.FlowTestsBaseclass):
  """Test the Flash dump flow."""

  def setUp(self):
    super(TestDumpFlashImage, self).setUp()
    self.vfs_overrider = test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.OS,
                                               test_lib.FakeFullVFSHandler)
    self.vfs_overrider.Start()
    test_lib.ClientFixture(self.client_id, token=self.token)

    # Create a fake component so we can launch the LoadComponent flow.
    fd = aff4.FACTORY.Create(
        "aff4:/config/components/grr-chipsec-component_1.2.2",
        collects.ComponentObject,
        mode="w",
        token=self.token)
    fd.Set(fd.Schema.COMPONENT(name="grr-chipsec-component", version="1.2.2"))
    fd.Close()

  def tearDown(self):
    self.vfs_overrider.Stop()
    super(TestDumpFlashImage, self).tearDown()

  def testDumpFlash(self):
    """Dump Flash Image."""
    client_mock = DumpFlashImageMock("StatFile", "MultiGetFile", "HashFile",
                                     "HashBuffer", "LoadComponent",
                                     "TransferBuffer", "DeleteGRRTempFiles")

    for _ in test_lib.TestFlowHelper("DumpFlashImage",
                                     client_mock,
                                     client_id=self.client_id,
                                     token=self.token):
      pass

    fd = aff4.FACTORY.Open(self.client_id.Add("spiflash"), token=self.token)
    self.assertEqual(fd.Read("10"), "\xff" * 10)

  def testUnknownChipset(self):
    """Fail to dump flash of unknown chipset."""
    client_mock = UnknownChipsetDumpMock("StatFile", "MultiGetFile", "HashFile",
                                         "HashBuffer", "LoadComponent",
                                         "TransferBuffer", "DeleteGRRTempFiles")

    # Manually start the flow in order to be able to read the logs
    flow_urn = flow.GRRFlow.StartFlow(client_id=self.client_id,
                                      flow_name="DumpFlashImage",
                                      token=self.token)

    for _ in test_lib.TestFlowHelper(flow_urn,
                                     client_mock,
                                     client_id=self.client_id,
                                     token=self.token):
      pass

    logs = aff4.FACTORY.Open(flow_urn.Add("Logs"), token=self.token)
    self.assertIn("Unknown chipset", [l.log_message for l in logs])

  def testFailedDumpImage(self):
    """Fail to dump flash."""
    client_mock = FailDumpMock("StatFile", "MultiGetFile", "LoadComponent",
                               "HashFile", "HashBuffer", "TransferBuffer",
                               "DeleteGRRTempFiles")

    for _ in test_lib.TestFlowHelper("DumpFlashImage",
                                     client_mock,
                                     client_id=self.client_id,
                                     token=self.token,
                                     check_flow_errors=False):
      pass


def main(argv):
  # Run the full test suite
  test_lib.GrrTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)
