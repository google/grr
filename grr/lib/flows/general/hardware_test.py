#!/usr/bin/env python
"""Tests for low-level flows."""

from grr.client.client_actions import tempfiles
from grr.client.components.chipsec_support.actions import chipsec_types
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


class DumpACPITableMock(action_mocks.ActionMock):

  ACPI_TABLES = {
      "DSDT": [
          chipsec_types.ACPITableData(table_address=0x1122334455667788,
                                      table_blob="\xAA" * 0xFF)
      ],
      "XSDT": [
          chipsec_types.ACPITableData(table_address=0x8877665544332211,
                                      table_blob="\xBB" * 0xFF)
      ],
      "SSDT": [
          chipsec_types.ACPITableData(table_address=0x1234567890ABCDEF,
                                      table_blob="\xCC" * 0xFF),
          chipsec_types.ACPITableData(table_address=0x2234567890ABCDEF,
                                      table_blob="\xDD" * 0xFF)
      ]
  }

  def LoadComponent(self, args):
    """Just assume that we can load the component during testing."""
    return [args]

  def DumpACPITable(self, args):
    acpi_tables = []
    logs = []

    if args.table_signature in self.ACPI_TABLES:
      acpi_tables = self.ACPI_TABLES[args.table_signature]
    else:
      logs.append("Unable to retrieve ACPI table with signature %s" %
                  args.table_signature)

    if args.logging:
      logs.append("log")

    response = chipsec_types.DumpACPITableResponse(acpi_tables=acpi_tables,
                                                   logs=logs)
    return [response]


class DumpACPITableTest(test_lib.FlowTestsBaseclass):

  def setUp(self):
    super(DumpACPITableTest, self).setUp()
    test_lib.WriteComponent(name="grr-chipsec-component",
                            version="1.2.2.2",
                            modules=["grr_chipsec"],
                            token=self.token)

  def testDumpValidACPITableOk(self):
    """Tests dumping ACPI table."""
    client_mock = DumpACPITableMock()
    table_signature_list = ["DSDT", "XSDT", "SSDT"]

    for _ in test_lib.TestFlowHelper("DumpACPITable",
                                     client_mock,
                                     table_signature_list=table_signature_list,
                                     client_id=self.client_id,
                                     token=self.token):
      pass

    fd = aff4.FACTORY.Open(
        self.client_id.Add("/devices/chipsec/acpi/tables/DSDT"),
        token=self.token)
    self.assertEqual(len(fd), 1)
    self.assertEqual(fd[0], DumpACPITableMock.ACPI_TABLES["DSDT"][0])

    fd = aff4.FACTORY.Open(
        self.client_id.Add("/devices/chipsec/acpi/tables/XSDT"),
        token=self.token)
    self.assertEqual(len(fd), 1)
    self.assertEqual(fd[0], DumpACPITableMock.ACPI_TABLES["XSDT"][0])

    fd = aff4.FACTORY.Open(
        self.client_id.Add("/devices/chipsec/acpi/tables/SSDT"),
        token=self.token)
    self.assertEqual(len(fd), 2)
    self.assertEqual(fd[0], DumpACPITableMock.ACPI_TABLES["SSDT"][0])
    self.assertEqual(fd[1], DumpACPITableMock.ACPI_TABLES["SSDT"][1])

  def testDumpInvalidACPITable(self):
    """Tests dumping nonexistent ACPI table."""
    client_mock = DumpACPITableMock()
    table_signature_list = ["ABC"]
    session_id = None

    for session_id in test_lib.TestFlowHelper(
        "DumpACPITable",
        client_mock,
        table_signature_list=table_signature_list,
        client_id=self.client_id,
        token=self.token):
      pass

    logs = aff4.FACTORY.Open(session_id.Add("Logs"), token=self.token)
    self.assertIn("Unable to retrieve ACPI table with signature ABC",
                  [log.log_message for log in logs])

  def testEmptyTableSignatureList(self):
    """Tests DumpACPITable with empty table_signature_list."""
    client_mock = DumpACPITableMock()
    table_signature_list = []

    with self.assertRaises(ValueError) as err:
      for _ in test_lib.TestFlowHelper(
          "DumpACPITable",
          client_mock,
          table_signature_list=table_signature_list,
          client_id=self.client_id,
          token=self.token):
        pass

    self.assertEqual(err.exception.message, "No ACPI table to dump.")


def main(argv):
  # Run the full test suite
  test_lib.GrrTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)
