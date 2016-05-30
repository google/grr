#!/usr/bin/env python
"""Test Chipsec client actions."""

__author__ = "Thiebaud Weksteen <tweksteen@gmail.com>"

import mock

from grr.client import vfs
from grr.client.components.chipsec_support import chipsec_types
from grr.client.components.chipsec_support import grr_chipsec
from grr.lib import flags
from grr.lib import test_lib
from grr.lib import utils


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
    spi_mock = mock.MagicMock()
    spi_mock.SPI = MockSPI
    chipset_mock = mock.MagicMock()

    chipset_mock.UnknownChipsetError = MockUnknownChipsetError

    self.chipset_patch = utils.Stubber(grr_chipsec, "chipset", chipset_mock)
    self.spi_patch = utils.Stubber(grr_chipsec, "spi", spi_mock)
    self.logger_patch = utils.Stubber(grr_chipsec, "logger", mock.MagicMock())

    self.chipset_patch.Start()
    self.spi_patch.Start()
    self.logger_patch.Start()

  def tearDown(self):
    self.chipset_patch.Stop()
    self.spi_patch.Stop()
    self.logger_patch.Stop()
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
    self.assertNotEqual(grr_chipsec.logger.call_count, 0)

  def testDumpFlashImageUnknownChipset(self):
    """By default, if the chipset is unknown, no exception is raised."""
    with utils.Stubber(grr_chipsec.chipset, "cs", FaultyChipset):
      args = chipsec_types.DumpFlashImageRequest()
      self.RunAction("DumpFlashImage", args)

  def testDumpFlashImageUnknownChipsetVerbose(self):
    """Test unknown chipset with verbose mode.

    If the chipset is unknown but verbose enabled, no exception is raised
    and at least one response should be returned with non-empty logs.
    """
    with utils.Stubber(grr_chipsec.chipset, "cs", FaultyChipset):
      args = chipsec_types.DumpFlashImageRequest(log_level=1)
      self.RunAction("DumpFlashImage", args)
      self.assertNotEquals(grr_chipsec.logger.call_count, 0)
      self.assertGreaterEqual(len(self.results), 1)
      self.assertNotEquals(len(self.results[0].logs), 0)
      self.assertEquals(self.results[0].path.path, "")


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
