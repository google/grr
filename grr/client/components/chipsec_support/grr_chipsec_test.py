#!/usr/bin/env python
"""Test Chipsec client actions."""

__author__ = "Thiebaud Weksteen <tweksteen@gmail.com>"

import collections
import sys
import mock

from grr.client import vfs
from grr.client.components.chipsec_support.actions import chipsec_types
from grr.lib import flags
from grr.lib import test_lib


class MockUnknownChipsetError(RuntimeError):
  pass


class MockSPI(mock.MagicMock):

  def __init__(self, chipset):
    pass

  def get_SPI_region(self, region):
    return (0, 0xffff, 0)

  def read_spi(self, offset, size):
    return "\xff" * size


class FaultyChipset(mock.MagicMock):

  def init(self, platform, load_driver):
    msg = "Unsupported Platform: VID = 0x0000, DID = 0x0000"
    raise MockUnknownChipsetError(msg)


class TestDumpFlashImage(test_lib.EmptyActionTest):
  """Test the client dump flash image action."""

  def setUp(self):
    super(TestDumpFlashImage, self).setUp()

    # Mock the interface for Chipsec
    chipsec_mock = mock.MagicMock()
    chipsec_mock.chipset = mock.MagicMock()
    chipsec_mock.chipset.UnknownChipsetError = MockUnknownChipsetError
    chipsec_mock.hal = mock.MagicMock()
    chipsec_mock.hal.spi = mock.MagicMock()
    chipsec_mock.hal.spi.SPI = MockSPI
    chipsec_mock.logger = mock.MagicMock()
    chipsec_mock.logger.logger = mock.MagicMock()

    self.mock = chipsec_mock

    mock_modules = {"chipsec": self.mock,
                    "chipsec.hal": self.mock.hal,
                    "chipsec.logger": self.mock.logger}

    self.chipsec_patch = mock.patch.dict(sys.modules, mock_modules)
    self.chipsec_patch.start()

    # Import the ClientAction to test with the Chipsec mock in place.
    # pylint: disable=g-import-not-at-top, unused-variable
    from grr.client.components.chipsec_support.actions import grr_chipsec
    # pylint: enable=g-import-not-at-top, unused-variable

    grr_chipsec.logger = self.mock.logger.logger
    grr_chipsec.spi = self.mock.hal.spi
    grr_chipsec.chipset = self.mock.chipset

  def tearDown(self):
    self.chipsec_patch.stop()
    super(TestDumpFlashImage, self).tearDown()

  def testDumpFlashImage(self):
    """Test the basic dump."""
    args = chipsec_types.DumpFlashImageRequest()
    result = self.RunAction("DumpFlashImage", args)[0]
    with vfs.VFSOpen(result.path) as image:
      self.assertEqual(image.read(0x20000), "\xff" * 0x10000)

  def testDumpFlashImageVerbose(self):
    """Test the basic dump with the verbose mode enabled."""
    args = chipsec_types.DumpFlashImageRequest(log_level=1)
    result = self.RunAction("DumpFlashImage", args)[0]
    with vfs.VFSOpen(result.path) as image:
      self.assertEqual(image.read(0x20000), "\xff" * 0x10000)
    self.assertNotEqual(self.mock.logger.logger.call_count, 0)

  def testDumpFlashImageUnknownChipset(self):
    """By default, if the chipset is unknown, no exception is raised."""
    self.mock.chipset.cs = FaultyChipset
    args = chipsec_types.DumpFlashImageRequest()
    self.RunAction("DumpFlashImage", args)

  def testDumpFlashImageUnknownChipsetVerbose(self):
    """Test unknown chipset with verbose mode.

    If the chipset is unknown but verbose enabled, no exception is raised
    and at least one response should be returned with non-empty logs.
    """
    self.mock.chipset.cs = FaultyChipset
    args = chipsec_types.DumpFlashImageRequest(log_level=1)
    self.RunAction("DumpFlashImage", args)
    self.assertNotEquals(self.mock.logger.logger.call_count, 0)
    self.assertGreaterEqual(len(self.results), 1)
    self.assertNotEquals(len(self.results[0].logs), 0)
    self.assertEquals(self.results[0].path.path, "")


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
        0xAABBCCDDEEFF0011: ("\xFF" * 0xFF, "\xEE" * 0xFF),
        0x1100FFEEDDCCBBAA: ("\xEE" * 0xFF, "\xFF" * 0xFF),
        0x1122334455667788: ("\xAB" * 0xFF, "\xCD" * 0xFF),
        0x1234567890ABCDEF: ("\xEF" * 0xFF, "\xFE" * 0xFF),
        0x2234567890ABCDEF: ("\xDC" * 0xFF, "\xBA" * 0xFF),
        0x3234567890ABCDEF: ("\xAA" * 0xFF, "\xBB" * 0xFF)
    }

  def get_ACPI_table(self, name):  # pylint: disable=invalid-name
    return [self.table_content[address] for address in self.tableList[name]]


class MockACPIReadingRestrictedArea(object):

  def __init__(self, unused_chipset):
    # Simulate /dev/mem error
    raise OSError("Operation not permitted")

  def get_ACPI_table(self, unused_name):  # pylint: disable=invalid-name
    return []


class TestDumpACPITable(test_lib.EmptyActionTest):

  def setUp(self):
    super(TestDumpACPITable, self).setUp()

    # Mock needed Chipsec modules and classes
    chipsec_mock = mock.MagicMock()
    chipsec_mock.chipset = mock.MagicMock()
    chipsec_mock.chipset.UnknownChipsetError = MockUnknownChipsetError
    chipsec_mock.hal = mock.MagicMock()
    chipsec_mock.hal.acpi = mock.MagicMock()
    chipsec_mock.hal.acpi.ACPI = MockACPI
    chipsec_mock.logger = mock.MagicMock()
    chipsec_mock.logger.logger = mock.MagicMock()

    self.mock = chipsec_mock

    mock_modules = {"chipsec": self.mock,
                    "chipsec.hal": self.mock.hal,
                    "chipsec.logger": self.mock.logger}

    self.chipsec_patch = mock.patch.dict(sys.modules, mock_modules)
    self.chipsec_patch.start()

    # pylint: disable=g-import-not-at-top, unused-variable
    from grr.client.components.chipsec_support.actions import grr_chipsec
    # pylint: enable=g-import-not-at-top, unused-variable

    # Use mock in the client action
    grr_chipsec.logger = self.mock.logger.logger
    grr_chipsec.acpi = self.mock.hal.acpi
    grr_chipsec.chipset = self.mock.chipset

  def tearDown(self):
    self.chipsec_patch.stop()
    super(TestDumpACPITable, self).tearDown()

  def testDumpValidSingleACPITable(self):
    """Tests basic valid ACPI table dump."""
    args = chipsec_types.DumpACPITableRequest(table_signature="DSDT")
    result = self.RunAction("DumpACPITable", args)[0]
    self.assertEqual(len(result.acpi_tables), 1)
    self.assertEqual(result.acpi_tables[0].table_address, 0xAABBCCDDEEFF0011)
    self.assertEqual(result.acpi_tables[0].table_blob,
                     "\xFF" * 0xFF + "\xEE" * 0xFF)

  def testDumpValidMultipleACPITables(self):
    """Tests valid ACPI table dump that would yield several tables."""
    args = chipsec_types.DumpACPITableRequest(table_signature="SSDT")
    result = self.RunAction("DumpACPITable", args)[0]
    self.assertEqual(len(result.acpi_tables), 3)
    self.assertEqual(result.acpi_tables[0].table_address, 0x1234567890ABCDEF)
    self.assertEqual(result.acpi_tables[0].table_blob,
                     "\xEF" * 0xFF + "\xFE" * 0xFF)
    self.assertEqual(result.acpi_tables[1].table_address, 0x2234567890ABCDEF)
    self.assertEqual(result.acpi_tables[1].table_blob,
                     "\xDC" * 0xFF + "\xBA" * 0xFF)
    self.assertEqual(result.acpi_tables[2].table_address, 0x3234567890ABCDEF)
    self.assertEqual(result.acpi_tables[2].table_blob,
                     "\xAA" * 0xFF + "\xBB" * 0xFF)

  def testDumpValidSingleACPITableVerbose(self):
    """Tests valid ACPI table dump with verbose mode enabled."""
    args = chipsec_types.DumpACPITableRequest(table_signature="XSDT",
                                              logging=True)
    result = self.RunAction("DumpACPITable", args)[0]
    self.assertEqual(result.acpi_tables[0].table_address, 0x1122334455667788)
    self.assertEqual(result.acpi_tables[0].table_blob,
                     "\xAB" * 0xFF + "\xCD" * 0xFF)
    self.assertNotEquals(self.mock.logger.logger.call_count, 0)

  def testDumpInvalidACPITable(self):
    """Tests dumping invalid ACPI table."""
    args = chipsec_types.DumpACPITableRequest(table_signature="INVALID_TABLE")
    result = self.RunAction("DumpACPITable", args)[0]
    self.assertNotEquals(len(result.logs), 0)

  def testDumpACPITableUnknownChipset(self):
    """By default, if the chipset is unknown, no exception is raised."""
    self.mock.chipset.cs = FaultyChipset
    args = chipsec_types.DumpACPITableRequest(table_signature="FACP")
    self.RunAction("DumpACPITable", args)

  def testDumpACPITableUnknownChipsetVerbose(self):
    """Tests unknown chipset with verbose mode.

    If the chipset is unknown but verbose enabled, no exception is raised
    and at least one response should be returned with non-empty logs.
    """
    self.mock.chipset.cs = FaultyChipset
    args = chipsec_types.DumpACPITableRequest(table_signature="FACP",
                                              logging=True)
    self.RunAction("DumpACPITable", args)
    self.assertNotEquals(self.mock.logger.logger.call_count, 0)
    self.assertGreaterEqual(len(self.results), 1)
    self.assertNotEquals(len(self.results[0].logs), 0)

  def testDumpACPITableTriggeringDevMemError(self):
    """Tests the condition where OSError is triggered due to using /dev/mem.

    No exception should be raised, and the log describing the error should be
    returned.
    """
    self.mock.acpi.ACPI = MockACPIReadingRestrictedArea
    args = chipsec_types.DumpACPITableRequest(table_signature="FACP")
    self.RunAction("DumpACPITable", args)
    self.assertGreaterEqual(len(self.results), 1)
    self.assertNotEquals(len(self.results[0].logs), 0)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
