#!/usr/bin/env python
"""Tests for low-level flows."""

from grr_response_client.client_actions import standard
from grr_response_client.client_actions import tempfiles
from grr.lib import flags
from grr.lib.rdfvalues import chipsec_types
from grr.server.grr_response_server import aff4
from grr.server.grr_response_server import flow
from grr.server.grr_response_server.aff4_objects import hardware as aff4_hardware
from grr.server.grr_response_server.flows.general import hardware
from grr.test_lib import action_mocks
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


class DumpFlashImageMock(action_mocks.ActionMock):
  """Mock the flash dumping on the client side."""

  def __init__(self, *args, **kwargs):
    super(DumpFlashImageMock, self).__init__(
        standard.HashBuffer, standard.HashFile, standard.GetFileStat,
        standard.TransferBuffer, tempfiles.DeleteGRRTempFiles)

  def DumpFlashImage(self, args):
    flash_fd, flash_path = tempfiles.CreateGRRTempFileVFS()
    flash_fd.write("\xff" * 1024)
    flash_fd.close()
    logs = ["test"] if args.log_level else []
    response = chipsec_types.DumpFlashImageResponse(path=flash_path, logs=logs)
    return [response]


class UnknownChipsetDumpMock(DumpFlashImageMock):

  def DumpFlashImage(self, args):
    logs = ["Unknown chipset"]
    response = chipsec_types.DumpFlashImageResponse(logs=logs)
    return [response]


class FailDumpMock(DumpFlashImageMock):

  def DumpFlashImage(self, args):
    raise IOError("Unexpected error")


class TestHardwareDumpFlashImage(flow_test_lib.FlowTestsBaseclass):
  """Test the Flash dump flow."""

  def setUp(self):
    super(TestHardwareDumpFlashImage, self).setUp()

    # Setup a specific client so the knowledge base is correctly
    # initialised for the artifact collection.
    self.client_id = self.SetupClient(0, system="Linux", os_version="16.04")

  def testDumpFlash(self):
    """Dump Flash Image."""
    client_mock = DumpFlashImageMock()

    flow_test_lib.TestFlowHelper(
        hardware.DumpFlashImage.__name__,
        client_mock,
        client_id=self.client_id,
        token=self.token)

    fd = aff4.FACTORY.Open(self.client_id.Add("spiflash"), token=self.token)
    self.assertEqual(fd.Read("10"), "\xff" * 10)

  def testUnknownChipset(self):
    """Fail to dump flash of unknown chipset."""
    client_mock = UnknownChipsetDumpMock()

    # Manually start the flow in order to be able to read the logs
    flow_urn = flow.GRRFlow.StartFlow(
        client_id=self.client_id,
        flow_name=hardware.DumpFlashImage.__name__,
        token=self.token)

    flow_test_lib.TestFlowHelper(
        flow_urn, client_mock, client_id=self.client_id, token=self.token)

    logs = flow.GRRFlow.LogCollectionForFID(flow_urn)
    self.assertIn("Unknown chipset", [l.log_message for l in logs])

  def testFailedDumpImage(self):
    """Fail to dump flash."""
    client_mock = FailDumpMock()

    flow_test_lib.TestFlowHelper(
        hardware.DumpFlashImage.__name__,
        client_mock,
        client_id=self.client_id,
        token=self.token,
        check_flow_errors=False)


class DumpACPITableMock(action_mocks.ActionMock):

  ACPI_TABLES = {
      "DSDT": [
          chipsec_types.ACPITableData(
              table_address=0x1122334455667788, table_blob="\xAA" * 0xFF)
      ],
      "XSDT": [
          chipsec_types.ACPITableData(
              table_address=0x8877665544332211, table_blob="\xBB" * 0xFF)
      ],
      "SSDT": [
          chipsec_types.ACPITableData(
              table_address=0x1234567890ABCDEF, table_blob="\xCC" * 0xFF),
          chipsec_types.ACPITableData(
              table_address=0x2234567890ABCDEF, table_blob="\xDD" * 0xFF)
      ]
  }

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

    response = chipsec_types.DumpACPITableResponse(
        acpi_tables=acpi_tables, logs=logs)
    return [response]


class DumpACPITableTest(flow_test_lib.FlowTestsBaseclass):

  def testDumpValidACPITableOk(self):
    """Tests dumping ACPI table."""
    client_mock = DumpACPITableMock()
    table_signature_list = ["DSDT", "XSDT", "SSDT"]
    client_id = self.SetupClient(0)

    flow_test_lib.TestFlowHelper(
        hardware.DumpACPITable.__name__,
        client_mock,
        table_signature_list=table_signature_list,
        client_id=client_id,
        token=self.token)

    fd = aff4_hardware.ACPITableDataCollection(
        client_id.Add("/devices/chipsec/acpi/tables/DSDT"))
    self.assertEqual(len(fd), 1)
    self.assertEqual(fd[0], DumpACPITableMock.ACPI_TABLES["DSDT"][0])

    fd = aff4_hardware.ACPITableDataCollection(
        client_id.Add("/devices/chipsec/acpi/tables/XSDT"))
    self.assertEqual(len(fd), 1)
    self.assertEqual(fd[0], DumpACPITableMock.ACPI_TABLES["XSDT"][0])

    fd = aff4_hardware.ACPITableDataCollection(
        client_id.Add("/devices/chipsec/acpi/tables/SSDT"))
    self.assertEqual(len(fd), 2)
    self.assertEqual(fd[0], DumpACPITableMock.ACPI_TABLES["SSDT"][0])
    self.assertEqual(fd[1], DumpACPITableMock.ACPI_TABLES["SSDT"][1])

  def testDumpInvalidACPITable(self):
    """Tests dumping nonexistent ACPI table."""
    client_mock = DumpACPITableMock()
    client_id = self.SetupClient(0)
    table_signature_list = ["ABC"]
    session_id = None

    session_id = flow_test_lib.TestFlowHelper(
        hardware.DumpACPITable.__name__,
        client_mock,
        table_signature_list=table_signature_list,
        client_id=client_id,
        token=self.token)

    logs = flow.GRRFlow.LogCollectionForFID(session_id)
    self.assertIn("Unable to retrieve ACPI table with signature ABC",
                  [log.log_message for log in logs])

  def testEmptyTableSignatureList(self):
    """Tests DumpACPITable with empty table_signature_list."""
    client_id = self.SetupClient(0)
    client_mock = DumpACPITableMock()
    table_signature_list = []

    with self.assertRaises(ValueError) as err:
      flow_test_lib.TestFlowHelper(
          hardware.DumpACPITable.__name__,
          client_mock,
          table_signature_list=table_signature_list,
          client_id=client_id,
          token=self.token)

    self.assertEqual(err.exception.message, "No ACPI table to dump.")


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
