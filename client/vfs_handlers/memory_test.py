#!/usr/bin/env python
"""Tests for the memory handler functions."""



import sys


# This has to be done now or it will fail later when sys.platform is changed.
import psutil  # pylint: disable=W0611

from grr.client import conf

# pylint: disable=C6204
# We want to test linux and mac.
old_platform = sys.platform
sys.platform = "darwin, linux"
from grr.client.vfs_handlers import memory
sys.platform = old_platform

from grr.lib import test_lib


class MockOSXMemory(memory.OSXMemory):

  class FakeFile(object):

    offset = 0

    # Implementing the file interface.
    # pylint: disable=C6409

    def read(self, length):
      return "X" * length

    def seek(self, offset):
      self.offset = offset

  def __init__(self):
    page_size = memory.OSXMemory.page_size
    self.mmap = [(0 * page_size, 1 * page_size),
                 (1 * page_size, 1 * page_size),
                 (2 * page_size, 8 * page_size),
                 (10 * page_size, 1 * page_size),
                 (15 * page_size, 1 * page_size),
                 (16 * page_size, 1 * page_size)]
    self.mem_dev = self.FakeFile()


class OSXMemoryTest(test_lib.GRRBaseTest):

  def testPartialRead(self):

    handler = MockOSXMemory()
    self.page_size = memory.OSXMemory.page_size

    last_region = handler.mmap[-1]
    self.assertEqual(handler.size,
                     last_region[0] + last_region[1])

    for start, length, valid in [
        # Just read a bit.
        (0, 100, 100),
        # Read over page boundary.
        (self.page_size - 100, 200, 200),
        # Read to page boundary.
        (self.page_size, 100, 100),
        # Read from page boundary.
        (self.page_size, 100, 100),
        # Read into invalid region (unmapped region starts at 11 * page_size).
        (11 * self.page_size - 500, 1100, 500),
        # Read out of invalid region (unmapped region ends at 15 * page_size).
        (15 * self.page_size - 500, 1100, 600),
        # Read inside the invalid region.
        (12 * self.page_size, 1000, 0),
        # Read over the invalid region.
        (0, handler.size, 13 * self.page_size),
        ]:
      handler.Seek(start)
      data = handler.Read(length)
      self.assertEqual(len(data), length)
      self.assertEqual(list(data).count("X"), valid)


def main(argv):
  test_lib.main(argv)

if __name__ == "__main__":
  conf.StartMain(main)
