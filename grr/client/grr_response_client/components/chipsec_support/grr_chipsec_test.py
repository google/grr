#!/usr/bin/env python
"""Test Chipsec client actions."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import collections
import sys
import mock

from chipsec.helper import oshelper

from grr_response_client import vfs
# If grr_response_client.components.chipsec_support.actions.grr_chipsec is
# imported here, it will import
# grr_response_client.components.chipsec_support.actions and fail (because of
# the circular import dependency).
#
# This is a terrible hack employed in grr_chipsec implementation since GRR
# components days. The idea is that we *must* import
# grr_response_client.components.chipsec_support.actions before
# grr_response_client.components.chipsec_support.actions.grr_chipsec to
# explicitly resolve the circular dependency.
from grr_response_client.components.chipsec_support import actions  # pylint: disable=unused-import
from grr_response_core.lib import flags
from grr_response_core.lib.rdfvalues import chipsec_types as rdf_chipsec_types
from grr.test_lib import client_test_lib
from grr.test_lib import test_lib


class MockUnknownChipsetError(RuntimeError):
  pass


class MockSPI(mock.MagicMock):

  def get_SPI_region(self, unused_region):  # pylint: disable=invalid-name
    return (0, 0xffff, 0)

  def read_spi(self, unused_offset, size):
    return b"\xff" * size


class UnsupportedChipset(mock.MagicMock):

  def init(self, unused_platform, unused_load_driver):
    msg = "Unsupported Platform: VID = 0x0000, DID = 0x0000"
    raise MockUnknownChipsetError(msg)


class FailingOsHelperChipset(mock.MagicMock):

  def init(self, unused_platform, unused_load_driver):
    msg = "Unable to open /sys/bus/pci/devices/0000:00:00.0/config"
    raise oshelper.OsHelperError(msg, -1)


class GRRChipsecTest(client_test_lib.EmptyActionTest):
  """Generic test class for GRR-Chipsec actions."""

  def setUp(self):
    # Mock the interface for Chipsec
    self.chipsec_mock = mock.MagicMock()
    self.chipsec_mock.chipset = mock.MagicMock()
    self.chipsec_mock.chipset.UnknownChipsetError = MockUnknownChipsetError
    self.chipsec_mock.hal = mock.MagicMock()
    self.chipsec_mock.logger = mock.MagicMock()

    mock_modules = {
        "chipsec": self.chipsec_mock,
        "chipsec.hal": self.chipsec_mock.hal,
    }

    self.chipsec_patch = mock.patch.dict(sys.modules, mock_modules)
    self.chipsec_patch.start()

    # Import the ClientAction to test with the Chipsec mock in place.
    # pylint: disable=g-import-not-at-top, unused-variable
    from grr_response_client.components.chipsec_support.actions import grr_chipsec
    # pylint: enable=g-import-not-at-top, unused-variable

    # Keep a reference to the module so child classes may mock its content.
    self.grr_chipsec_module = grr_chipsec
    self.grr_chipsec_module.chipset = self.chipsec_mock.chipset
    self.grr_chipsec_module.logger = self.chipsec_mock.logger

  def tearDown(self):
    self.chipsec_patch.stop()


class TestChipsecDumpFlashImage(GRRChipsecTest):
  """Test the client dump flash image action."""

  def setUp(self):
    super(TestChipsecDumpFlashImage, self).setUp()
    self.chipsec_mock.hal.spi = mock.MagicMock()
    self.chipsec_mock.hal.spi.SPI = MockSPI
    self.grr_chipsec_module.spi = self.chipsec_mock.hal.spi

  def testDumpFlashImage(self):
    """Test the basic dump."""
    args = rdf_chipsec_types.DumpFlashImageRequest()
    result = self.RunAction(self.grr_chipsec_module.DumpFlashImage, args)[0]
    with vfs.VFSOpen(result.path) as image:
      self.assertEqual(image.read(0x20000), b"\xff" * 0x10000)

  def testDumpFlashImageVerbose(self):
    """Test the basic dump with the verbose mode enabled."""
    args = rdf_chipsec_types.DumpFlashImageRequest(log_level=1)
    result = self.RunAction(self.grr_chipsec_module.DumpFlashImage, args)[0]
    with vfs.VFSOpen(result.path) as image:
      self.assertEqual(image.read(0x20000), b"\xff" * 0x10000)
    self.assertNotEqual(self.chipsec_mock.logger.logger.call_count, 0)

  def testDumpFlashImageUnknownChipset(self):
    """By default, if the chipset is unknown, no exception is raised."""
    self.chipsec_mock.chipset.cs = UnsupportedChipset
    args = rdf_chipsec_types.DumpFlashImageRequest()
    self.RunAction(self.grr_chipsec_module.DumpFlashImage, args)

  def testDumpFlashImageUnknownChipsetVerbose(self):
    """Test unknown chipset with verbose mode.

    If the chipset is unknown but verbose enabled, no exception is raised
    and at least one response should be returned with non-empty logs.
    """
    self.chipsec_mock.chipset.cs = UnsupportedChipset
    args = rdf_chipsec_types.DumpFlashImageRequest(log_level=1)
    self.RunAction(self.grr_chipsec_module.DumpFlashImage, args)
    self.assertNotEquals(self.chipsec_mock.logger.logger.call_count, 0)
    self.assertGreaterEqual(len(self.results), 1)
    self.assertNotEquals(len(self.results[0].logs), 0)
    self.assertEqual(self.results[0].path.path, "")

  def testDumpFlashImageOsHelperErrorChipset(self):
    """If an exception is raised by the helper layer, handle it."""
    self.chipsec_mock.chipset.cs = FailingOsHelperChipset
    args = rdf_chipsec_types.DumpFlashImageRequest()
    self.RunAction(self.grr_chipsec_module.DumpFlashImage, args)


class MockACPI(object):

  def __init__(self, unused_chipset):
    self.tableList = {  # pylint: disable=invalid-name
        "DSDT": [(0xAABBCCDDEEFF0011)],
        "FACP": [(0x1100FFEEDDCCBBAA)],
        "XSDT": [(0x1122334455667788)],
        "SSDT": [(0x1234567890ABCDEF), (0x2234567890ABCDEF),
                 (0x3234567890ABCDEF)]
    }

    # Mimic the behaviour of tableList in Chipsec
    # pylint: disable=invalid-name
    self.tableList = collections.defaultdict(list, self.tableList)
    # pylint: enable=invalid-name

    # key: header, content
    self.table_content = {
        0xAABBCCDDEEFF0011: (b"\xFF" * 0xFF, b"\xEE" * 0xFF),
        0x1100FFEEDDCCBBAA: (b"\xEE" * 0xFF, b"\xFF" * 0xFF),
        0x1122334455667788: (b"\xAB" * 0xFF, b"\xCD" * 0xFF),
        0x1234567890ABCDEF: (b"\xEF" * 0xFF, b"\xFE" * 0xFF),
        0x2234567890ABCDEF: (b"\xDC" * 0xFF, b"\xBA" * 0xFF),
        0x3234567890ABCDEF: (b"\xAA" * 0xFF, b"\xBB" * 0xFF)
    }

  def get_ACPI_table(self, name):  # pylint: disable=invalid-name
    return [self.table_content[address] for address in self.tableList[name]]


class MockACPIReadingRestrictedArea(object):

  def __init__(self, unused_chipset):
    # Simulate /dev/mem error
    raise OSError("Operation not permitted")

  def get_ACPI_table(self, unused_name):  # pylint: disable=invalid-name
    return []


class TestDumpACPITable(GRRChipsecTest):

  def setUp(self):
    super(TestDumpACPITable, self).setUp()
    self.chipsec_mock.hal.acpi = mock.MagicMock()
    self.chipsec_mock.hal.acpi.ACPI = MockACPI

    self.grr_chipsec_module.acpi = self.chipsec_mock.hal.acpi

  def testDumpValidSingleACPITable(self):
    """Tests basic valid ACPI table dump."""
    args = rdf_chipsec_types.DumpACPITableRequest(table_signature="DSDT")
    result = self.RunAction(self.grr_chipsec_module.DumpACPITable, args)[0]
    self.assertLen(result.acpi_tables, 1)
    self.assertEqual(result.acpi_tables[0].table_address, 0xAABBCCDDEEFF0011)
    self.assertEqual(result.acpi_tables[0].table_blob,
                     b"\xFF" * 0xFF + b"\xEE" * 0xFF)

  def testDumpValidMultipleACPITables(self):
    """Tests valid ACPI table dump that would yield several tables."""
    args = rdf_chipsec_types.DumpACPITableRequest(table_signature="SSDT")
    result = self.RunAction(self.grr_chipsec_module.DumpACPITable, args)[0]
    self.assertLen(result.acpi_tables, 3)
    self.assertEqual(result.acpi_tables[0].table_address, 0x1234567890ABCDEF)
    self.assertEqual(result.acpi_tables[0].table_blob,
                     b"\xEF" * 0xFF + b"\xFE" * 0xFF)
    self.assertEqual(result.acpi_tables[1].table_address, 0x2234567890ABCDEF)
    self.assertEqual(result.acpi_tables[1].table_blob,
                     b"\xDC" * 0xFF + b"\xBA" * 0xFF)
    self.assertEqual(result.acpi_tables[2].table_address, 0x3234567890ABCDEF)
    self.assertEqual(result.acpi_tables[2].table_blob,
                     b"\xAA" * 0xFF + b"\xBB" * 0xFF)

  def testDumpValidSingleACPITableVerbose(self):
    """Tests valid ACPI table dump with verbose mode enabled."""
    args = rdf_chipsec_types.DumpACPITableRequest(
        table_signature="XSDT", logging=True)
    result = self.RunAction(self.grr_chipsec_module.DumpACPITable, args)[0]
    self.assertEqual(result.acpi_tables[0].table_address, 0x1122334455667788)
    self.assertEqual(result.acpi_tables[0].table_blob,
                     b"\xAB" * 0xFF + b"\xCD" * 0xFF)
    self.assertNotEquals(self.chipsec_mock.logger.logger.call_count, 0)

  def testDumpInvalidACPITable(self):
    """Tests dumping invalid ACPI table."""
    args = rdf_chipsec_types.DumpACPITableRequest(
        table_signature="INVALID_TABLE")
    result = self.RunAction(self.grr_chipsec_module.DumpACPITable, args)[0]
    self.assertNotEquals(len(result.logs), 0)

  def testDumpACPITableUnknownChipset(self):
    """By default, if the chipset is unknown, no exception is raised."""
    self.chipsec_mock.chipset.cs = UnsupportedChipset
    args = rdf_chipsec_types.DumpACPITableRequest(table_signature="FACP")
    self.RunAction(self.grr_chipsec_module.DumpACPITable, args)

  def testDumpACPITableUnknownChipsetVerbose(self):
    """Tests unknown chipset with verbose mode.

    If the chipset is unknown but verbose enabled, no exception is raised
    and at least one response should be returned with non-empty logs.
    """
    self.chipsec_mock.chipset.cs = UnsupportedChipset
    args = rdf_chipsec_types.DumpACPITableRequest(
        table_signature="FACP", logging=True)
    self.RunAction(self.grr_chipsec_module.DumpACPITable, args)
    self.assertNotEquals(self.chipsec_mock.logger.logger.call_count, 0)
    self.assertGreaterEqual(len(self.results), 1)
    self.assertNotEquals(len(self.results[0].logs), 0)

  def testDumpACPITableTriggeringDevMemError(self):
    """Tests the condition where OSError is triggered due to using /dev/mem.

    No exception should be raised, and the log describing the error should be
    returned.
    """
    self.chipsec_mock.acpi.ACPI = MockACPIReadingRestrictedArea
    args = rdf_chipsec_types.DumpACPITableRequest(table_signature="FACP")
    self.RunAction(self.grr_chipsec_module.DumpACPITable, args)
    self.assertGreaterEqual(len(self.results), 1)
    self.assertNotEquals(len(self.results[0].logs), 0)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
