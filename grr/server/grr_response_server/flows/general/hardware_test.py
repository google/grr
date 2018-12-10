#!/usr/bin/env python
"""Tests for low-level flows."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_client.client_actions import standard
from grr_response_client.client_actions import tempfiles
from grr_response_core.lib import flags
from grr_response_core.lib.rdfvalues import chipsec_types as rdf_chipsec_types
from grr_response_server import aff4
from grr_response_server import data_store
from grr_response_server import flow
from grr_response_server.flows.general import hardware
from grr.test_lib import action_mocks
from grr.test_lib import db_test_lib
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
    flash_fd.write(b"\xff" * 1024)
    flash_fd.close()
    logs = ["test"] if args.log_level else []
    response = rdf_chipsec_types.DumpFlashImageResponse(
        path=flash_path, logs=logs)
    return [response]


class UnknownChipsetDumpMock(DumpFlashImageMock):

  def DumpFlashImage(self, args):
    logs = ["Unknown chipset"]
    response = rdf_chipsec_types.DumpFlashImageResponse(logs=logs)
    return [response]


class FailDumpMock(DumpFlashImageMock):

  def DumpFlashImage(self, args):
    raise IOError("Unexpected error")


@db_test_lib.DualDBTest
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

    flow_id = flow_test_lib.TestFlowHelper(
        hardware.DumpFlashImage.__name__,
        client_mock,
        client_id=self.client_id,
        token=self.token)

    results = flow_test_lib.GetFlowResults(self.client_id, flow_id)
    self.assertLen(results, 1)
    if data_store.AFF4Enabled():
      stat_entry = results[0]
      aff4_path = stat_entry.pathspec.AFF4Path(self.client_id)
      fd = aff4.FACTORY.Open(aff4_path, token=self.token)
      self.assertEqual(fd.Read("10"), b"\xff" * 10)

  def testUnknownChipset(self):
    """Fail to dump flash of unknown chipset."""
    client_mock = UnknownChipsetDumpMock()

    flow_id = flow_test_lib.TestFlowHelper(
        hardware.DumpFlashImage.__name__,
        client_mock,
        client_id=self.client_id,
        token=self.token)

    if data_store.RelationalDBFlowsEnabled():
      log_items = data_store.REL_DB.ReadFlowLogEntries(
          self.client_id.Basename(), flow_id, 0, 100)
      logs = [l.message for l in log_items]
    else:
      log_items = flow.GRRFlow.LogCollectionForFID(flow_id)
      logs = [l.log_message for l in log_items]

    self.assertIn("Unknown chipset", logs)

  def testFailedDumpImage(self):
    """Fail to dump flash."""
    client_mock = FailDumpMock()

    with test_lib.SuppressLogs():
      flow_test_lib.TestFlowHelper(
          hardware.DumpFlashImage.__name__,
          client_mock,
          client_id=self.client_id,
          token=self.token,
          check_flow_errors=False)


class DumpACPITableMock(action_mocks.ActionMock):

  ACPI_TABLES = {
      "DSDT": [
          rdf_chipsec_types.ACPITableData(
              table_address=0x1122334455667788,
              table_blob=b"\xAA" * 0xFF,
              table_signature="DSDT")
      ],
      "XSDT": [
          rdf_chipsec_types.ACPITableData(
              table_address=0x8877665544332211,
              table_blob=b"\xBB" * 0xFF,
              table_signature="XSDT")
      ],
      "SSDT": [
          rdf_chipsec_types.ACPITableData(
              table_address=0x1234567890ABCDEF,
              table_blob=b"\xCC" * 0xFF,
              table_signature="SSDT"),
          rdf_chipsec_types.ACPITableData(
              table_address=0x2234567890ABCDEF,
              table_blob=b"\xDD" * 0xFF,
              table_signature="SSDT")
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

    response = rdf_chipsec_types.DumpACPITableResponse(
        acpi_tables=acpi_tables, logs=logs)
    return [response]


@db_test_lib.DualDBTest
class DumpACPITableTest(flow_test_lib.FlowTestsBaseclass):

  def testDumpValidACPITableOk(self):
    """Tests dumping ACPI table."""
    client_mock = DumpACPITableMock()
    table_signature_list = ["DSDT", "XSDT", "SSDT"]
    client_id = self.SetupClient(0)

    flow_id = flow_test_lib.TestFlowHelper(
        hardware.DumpACPITable.__name__,
        client_mock,
        table_signature_list=table_signature_list,
        client_id=client_id,
        token=self.token)

    if data_store.RelationalDBFlowsEnabled():
      results = [
          r.payload for r in data_store.REL_DB.ReadFlowResults(
              client_id.Basename(), flow_id, 0, 100)
      ]
    else:
      results = list(flow.GRRFlow.ResultCollectionForFID(flow_id))

    self.assertLen(results, 4)

    dsdt_tables = [
        table for table in results if table.table_signature == "DSDT"
    ]
    xsdt_tables = [
        table for table in results if table.table_signature == "XSDT"
    ]
    ssdt_tables = [
        table for table in results if table.table_signature == "SSDT"
    ]

    self.assertCountEqual(DumpACPITableMock.ACPI_TABLES["DSDT"], dsdt_tables)
    self.assertCountEqual(DumpACPITableMock.ACPI_TABLES["XSDT"], xsdt_tables)
    self.assertCountEqual(DumpACPITableMock.ACPI_TABLES["SSDT"], ssdt_tables)

  def testDumpInvalidACPITable(self):
    """Tests dumping nonexistent ACPI table."""
    client_mock = DumpACPITableMock()
    client_id = self.SetupClient(0)
    table_signature_list = ["ABC"]

    flow_id = flow_test_lib.TestFlowHelper(
        hardware.DumpACPITable.__name__,
        client_mock,
        table_signature_list=table_signature_list,
        client_id=client_id,
        token=self.token)

    if data_store.RelationalDBFlowsEnabled():
      log_items = data_store.REL_DB.ReadFlowLogEntries(client_id.Basename(),
                                                       flow_id, 0, 100)
      logs = [l.message for l in log_items]
    else:
      log_items = flow.GRRFlow.LogCollectionForFID(flow_id)
      logs = [l.log_message for l in log_items]

    self.assertIn("Unable to retrieve ACPI table with signature ABC", logs)

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
