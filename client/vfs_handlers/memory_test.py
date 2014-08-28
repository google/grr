#!/usr/bin/env python
"""Tests for the memory handler functions."""


import StringIO


# pylint: disable=unused-import,g-bad-import-order
from grr.client import client_plugins
# pylint: enable=unused-import,g-bad-import-order

from grr.client.vfs_handlers import memory
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib import utils


class FakeFile(object):
  """A Fake file object."""
  offset = 0

  # Implementing the file interface.
  # pylint: disable=g-bad-name

  def read(self, length):
    return "X" * length

  def seek(self, offset):
    self.offset = offset

  def tell(self):
    return self.offset


class MockOSXMemory(memory.OSXMemory):

  def __init__(self):
    page_size = memory.OSXMemory.page_size
    self.runs = [(0 * page_size, 1 * page_size),
                 (1 * page_size, 1 * page_size),
                 (2 * page_size, 8 * page_size),
                 (10 * page_size, 1 * page_size),
                 (15 * page_size, 1 * page_size),
                 (16 * page_size, 1 * page_size)]
    self.fd = FakeFile()


class OSXMemoryTest(test_lib.GRRBaseTest):

  def GetVFSHandler(self):
    return MockOSXMemory()

  def testPartialRead(self):
    handler = self.GetVFSHandler()
    self.page_size = handler.page_size

    last_region = handler.runs[-1]
    self.assertEqual(handler.size,
                     last_region[0] + last_region[1])

    for start, length, valid in [
        # Just read a bit.
        (0, 100, 100),
        # Read over page boundary.
        (self.page_size - 100, 200, 200),
        # Read to page boundary.
        (self.page_size - 100, 100, 100),
        # Read from page boundary.
        (self.page_size, 100, 100),
        # Read into invalid region (unmapped region starts at 11 * page_size).
        (11 * self.page_size - 500, 1100, 500),
        # Read out of invalid region (unmapped region ends at 15 * page_size).
        (15 * self.page_size - 500, 1100, 600),
        # Read inside the invalid region.
        (12 * self.page_size, 1000, 0),
        # Read over the invalid region.
        (0, 17 * self.page_size, 13 * self.page_size),
        ]:
      handler.Seek(start)
      data = handler.Read(length)
      self.assertEqual(len(data), length)
      self.assertEqual(list(data).count("X"), valid)

    # Check that reading the unmapped region zero pads:
    handler.Seek(11 * self.page_size - 5)
    data = handler.Read(100)

    # Should return X for the valid region and 0 for the invalid region.
    self.assertEqual(data, "X" * 5 + "\x00" * 95)


class TestLinuxMemory(OSXMemoryTest):
  """Test the linux memory handler."""

  IOMEM = """
00000000-00001000 : System RAM
00001000-00002000 : System RAM
00002000-0000a000 : System RAM
0000a000-0000b000 : System RAM
0000f000-00010000 : System RAM
00010000-00011000 : System RAM
00096400-0009ffff : reserved
000a0000-000bffff : PCI Bus 0000:00
000c0000-000dffff : PCI Bus 0000:40
  000c0000-000dffff : PCI Bus 0000:00
    000c0000-000ce7ff : Video ROM
    000ce800-000cf7ff : Adapter ROM
    000cf800-000cfbff : Adapter ROM
    000d0000-000d85ff : Adapter ROM
000e0000-000fffff : reserved
  000f0000-000fffff : System ROM
00100000-cb3e1fff : System RAM
  01000000-015e2222 : Kernel code
  015e2223-01a9537f : Kernel data
  01b81000-01c82fff : Kernel bss
cb3e2000-cb7f3fff : reserved
cb7f4000-cb9c4fff : ACPI Non-volatile Storage
cb9c5000-cbae6fff : reserved
cbae7000-cbffffff : ACPI Non-volatile Storage
  ff000000-ffffffff : pnp 00:0c
100000000-82fffffff : System RAM
3c0000000000-3c007fffffff : PCI Bus 0000:00
"""

  def GetVFSHandler(self):

    def FakeOpen(filename, mode="r"):
      """The linux driver just opens the device."""
      # It uses /proc/iomem to find the protected areas.
      if filename == "/proc/iomem":
        return StringIO.StringIO(self.IOMEM)

      self.assertEqual(filename, "/dev/pmem")
      self.assertEqual(mode, "rb")
      return FakeFile()

    with utils.Stubber(memory, "open", FakeOpen):
      result = memory.LinuxMemory(None, pathspec=rdfvalue.PathSpec(
          path="/dev/pmem", pathtype=rdfvalue.PathSpec.PathType.MEMORY))

      self.assertEqual(result.size, 0x82fffffff)
      return result


class Win32FileMock(object):
  GENERIC_READ = GENERIC_WRITE = FILE_SHARE_READ = FILE_SHARE_WRITE = 0
  OPEN_EXISTING = FILE_ATTRIBUTE_NORMAL = 0

  def CreateFile(self, path, *_):
    self.path = path
    return path

  def ReadFile(self, fd, length):
    assert self.path == fd
    return True, "X" * length

  def SetFilePointer(self, fd, offset, whence=0):
    assert fd == self.path
    self.offset = offset
    _ = whence

  def DeviceIoControl(self, fd, *_):
    assert fd == self.path
    return ("0070180000000000"    # CR3
            "b11d000000000000"    # NtBuildNumber
            "00a0800200f8ffff"    # KernBase
            "a0909f0200f8ffff"    # KDBG
            "00ad9f0200f8ffff" +  # KPCR
            "0000000000000000" * 31 +
            "7872ab0200f8ffff"    # PfnDataBase
            "d0d6a40200f8ffff"    # PsLoadedModuleList
            "d0f3a20200f8ffff" +  # PsActiveProcessHead
            "0000000000000000" * 0xFF +  # Padding
            "0700000000000000"    # NumberOfRuns
            "0000000000000000" "0010000000000000"
            "0010000000000000" "0010000000000000"
            "0020000000000000" "0080000000000000"
            "00a0000000000000" "0010000000000000"
            "00f0000000000000" "0010000000000000"
            "0000010000000000" "0010000000000000"
            "0000000001000000" "FFFFFF2F07000000").decode("hex")


class TestWindowsMemory(OSXMemoryTest):
  """Test the windows memory handler."""

  def GetVFSHandler(self):
    result = memory.WindowsMemory(None, pathspec=rdfvalue.PathSpec(
        path=r"\\.\pmem", pathtype=rdfvalue.PathSpec.PathType.MEMORY))

    self.assertEqual(result.size, 0x82fffffff)
    return result

  def testPartialRead(self):
    with utils.Stubber(memory, "win32file", Win32FileMock()):
      super(TestWindowsMemory, self).testPartialRead()


def main(argv):
  test_lib.main(argv)

if __name__ == "__main__":
  flags.StartMain(main)
