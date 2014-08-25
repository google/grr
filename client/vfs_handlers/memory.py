#!/usr/bin/env python
"""VFS Handler which provides access to the raw physical memory.

Memory access is provided by use of a special driver. Note that it is preferred
to use this VFS handler rather than directly access the raw handler since this
handler protects the system from access to unmapped memory regions such as DMA
regions. It is always safe to access all of memory using this handler.
"""


import array
import re
import struct
import sys

from grr.client import vfs
from grr.lib import rdfvalue

# pylint: disable=g-import-not-at-top
try:
  import win32file
except ImportError:
  win32file = None

try:
  import fcntl
except ImportError:
  fcntl = None
# pylint: enable=g-import-not-at-top


class MemoryVFS(vfs.VFSHandler):
  """A base class for memory drivers."""
  page_size = 0x1000

  def __init__(self, base_fd, pathspec=None, progress_callback=None):
    self.fd = base_fd
    self.pathspec = pathspec

  @classmethod
  def Open(cls, fd, component, pathspec=None, progress_callback=None):
    _ = pathspec, progress_callback
    return cls(fd, pathspec=component, progress_callback=progress_callback)

  def IsDirectory(self):
    return False

  def Stat(self):
    result = rdfvalue.StatEntry(st_size=self.size, pathspec=self.pathspec)
    return result

  def Read(self, length):
    """Read from the memory device, null padding the ranges."""
    result = ""
    while length > 0 and self.offset < self.size:
      data = self._PartialRead(length)
      if not data: break

      length -= len(data)
      self.offset += len(data)
      result += data

    return result

  def _PartialRead(self, length):
    last_end = 0
    # Iterate over all the runs and see which one encloses the current file
    # pointer.
    for start, run_length in self.runs:

      # File pointer falls between the last range end and before the current
      # range start (i.e. outside the valid ranges).
      if last_end <= self.offset < start:
        # Zero pad it
        return "\x00" * min(length, start - self.offset)

      last_end = end = start + run_length
      # File pointer falls within a valid range, just read from the device.
      if start <= self.offset < end:
        to_read = min(length, end - self.offset)
        return self._ReadRandom(self.offset, to_read)


class LinuxMemory(MemoryVFS):
  """A Linux memory VFS driver."""

  def __init__(self, base_fd, pathspec=None, progress_callback=None):
    """Open the raw memory image.

    Args:
      base_fd: The file like object we read this component from.
      pathspec: An optional pathspec to open directly.
      progress_callback: A callback to indicate that the open call is still
                         working but needs more time.

    Raises:
      IOError: If the file can not be opened.
    """
    super(LinuxMemory, self).__init__(base_fd, pathspec=pathspec,
                                      progress_callback=progress_callback)
    if self.base_fd is not None:
      raise IOError("Memory driver must be a top level VFS handler.")

    # TODO(user): What should we do if can not read the maps? Should we try
    # to obtain these from the driver? Should we just allow reading anywhere?
    self.runs = self.GetMemoryMap()
    self.fd = open(pathspec.path, "rb")
    self.size = self.runs[-1][0] + self.runs[-1][1]

  def GetMemoryMap(self):
    """Read the memory map from /proc/iomem."""
    runs = []
    for line in open("/proc/iomem"):
      if "System RAM" in line:
        m = re.match("([^-]+)-([^ ]+)", line)
        if m:
          start = int(m.group(1), 16)
          end = int(m.group(2), 16)
          runs.append((start, end - start))

    return sorted(runs)

  def _ReadRandom(self, offset, length):
    self.fd.seek(offset)
    return self.fd.read(length)


class WindowsMemory(MemoryVFS):
  """Read the raw memory."""
  # This is the dtb and kdbg if available
  cr3 = None
  kdbg = None

  FIELDS = (["CR3", "NtBuildNumber", "KernBase", "KDBG"] +
            ["KPCR%s" % i for i in range(32)] +
            ["PfnDataBase", "PsLoadedModuleList", "PsActiveProcessHead"] +
            ["Padding%s" % i for i in range(0xff)] +
            ["NumberOfRuns"])

  @staticmethod
  def CtlCode(device_type, function, method, access):
    return (device_type << 16) | (access << 14) | (function << 2) | method

  def __init__(self, base_fd, pathspec=None, progress_callback=None):
    """Open the raw memory image.

    Args:
      base_fd: The file like object we read this component from.
      pathspec: An optional pathspec to open directly.
      progress_callback: A callback to indicate that the open call is still
                         working but needs more time.

    Raises:
      IOError: If the file can not be opened.
    """
    super(WindowsMemory, self).__init__(base_fd, pathspec=pathspec,
                                        progress_callback=progress_callback)
    if self.base_fd is not None:
      raise IOError("Memory driver must be a top level.")

    # IOCTLS for interacting with the driver.
    self.info_ioctrl = self.CtlCode(0x22, 0x103, 0, 3)

    # We need to use win32 api to open the device.
    self.fd = win32file.CreateFile(
        pathspec.path,
        win32file.GENERIC_READ | win32file.GENERIC_WRITE,
        win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE,
        None,
        win32file.OPEN_EXISTING,
        win32file.FILE_ATTRIBUTE_NORMAL,
        None)

    result = win32file.DeviceIoControl(
        self.fd, self.info_ioctrl, "", 102400, None)

    fmt_string = "Q" * len(self.FIELDS)
    memory_parameters = dict(zip(self.FIELDS,
                                 struct.unpack_from(fmt_string, result)))
    self.cr3 = memory_parameters["CR3"]
    self.kdbg = memory_parameters["KDBG"]

    offset = struct.calcsize(fmt_string)
    self.runs = []
    self.size = 0
    for x in range(memory_parameters["NumberOfRuns"]):
      start, length = struct.unpack_from("QQ", result, x * 16 + offset)
      if length == 0: break

      self.runs.append((start, length))
      self.size = start + length

  def _ReadRandom(self, offset, length):
    win32file.SetFilePointer(self.fd, offset, 0)

    _, data = win32file.ReadFile(self.fd, length)

    return data


class OSXMemory(MemoryVFS):
  """Read physical memory from pmem driver."""
  # From the drivers pmem_ioctls.h
  pmem_ioc_get_mmap = 0x80087000
  pmem_ioc_get_mmap_size = 0x40047001
  pmem_ioc_get_mmap_desc_size = 0x40047002
  pmem_ioc_get_dtb = 0x40087003
  # (Type, Pad, PhysicalStart, VirtualStart, NumberOfPages, Attribute)
  format_efimemoryrange = "IIQQQQ"

  valid_memory_types = (1,   # Loader Code
                        2,   # Loader Data
                        3,   # BS Code
                        4,   # BS Data
                        5,   # RTS Code
                        6,   # RTS Data
                        7,   # Conventional
                        9,   # ACPI Reclaim
                        10,  # ACPI Memory NVS
                        13,  # Pal Code
                        14)  # Max Memory Type

  def __init__(self, base_fd=None, pathspec=None, progress_callback=None):
    """Open the memory device and get the memory map.

    Args:
      base_fd: The file like object we read this component from.
      pathspec: An optional pathspec to open directly.
      progress_callback: A callback to indicate that the open call is still
                         working but needs more time.

    Raises:
      IOError: If the file can not be opened or an ioctl fails.
    """
    super(OSXMemory, self).__init__(base_fd, pathspec=pathspec,
                                    progress_callback=progress_callback)
    if self.base_fd is not None:
      raise IOError("Memory driver must be a top level.")

    self.fd = open(pathspec.path, "rb")
    self.runs = self.GetMemoryMap(self.fd)

  @property
  def size(self):
    start, length = self.runs[-1]
    return start + length

  @staticmethod
  def GetCR3(mem_dev):
    """Query the memory driver for the kernels CR3 value.

    Args:
      mem_dev: An open file descriptor to the pmem driver.

    Returns:
      The Directory Table Base of the kernels address space
    """
    buf = array.array("L", [0])
    fcntl.ioctl(mem_dev, OSXMemory.pmem_ioc_get_dtb, buf, True)
    return buf[0]

  @staticmethod
  def GetMemoryMap(mem_dev):
    """Obtain and parse the memory map.

    Args:
      mem_dev: An open file descriptor to the pmem driver.

    Returns:
      List of tuples (start_address, number_of_pages)
    """
    size, desc_size = OSXMemory._GetBinaryMemoryMapDimensions(mem_dev)
    mmap = OSXMemory._GetBinaryMemoryMap(mem_dev, size)
    return OSXMemory._ParseBinaryMemoryMap(mmap, size, desc_size)

  @staticmethod
  def _GetBinaryMemoryMapDimensions(mem_dev):
    """Query the memory driver for the memory map dimensions.

    Args:
      mem_dev: An open file descriptor to the pmem driver.

    Returns:
      A Tuple (size, descriptor_size).
    """
    buf = array.array("L", [0])
    fcntl.ioctl(mem_dev, OSXMemory.pmem_ioc_get_mmap_size, buf, True)
    mmap_size = buf[0]
    fcntl.ioctl(mem_dev, OSXMemory.pmem_ioc_get_mmap_desc_size, buf, True)
    mmap_desc_size = buf[0]
    return (mmap_size, mmap_desc_size)

  @staticmethod
  def _GetBinaryMemoryMap(mem_dev, mmap_size):
    """Query the memory driver for the memory map.

    Args:
      mem_dev: An open file descriptor to the pmem driver.
      mmap_size: Size of the memory map in bytes.

    Returns:
      The binary memory map (as an array of EfiMemoryRange structs).
    """
    mmap_buf = array.array("B", " " * mmap_size)
    ptr_mmap_buf = struct.pack("Q", mmap_buf.buffer_info()[0])
    fcntl.ioctl(mem_dev, OSXMemory.pmem_ioc_get_mmap, ptr_mmap_buf)
    return mmap_buf.tostring()

  @staticmethod
  def _ParseBinaryMemoryMap(mmap, size, desc_size):
    """Converts a binary EFI memory map to python tuples of memory segments.

    Args:
      mmap: The binary memory map, an array of EfiMemoryRange structs.
      size: The size in bytes of the memory map.
      desc_size: The size in bytes of an individual EfiMemoryRange struct.

    Returns:
      List of tuples (start_address, length of segment in bytes)
    """
    num_descriptors = size / desc_size
    result = list()

    for x in xrange(num_descriptors):
      (seg_type, _, start, _, pages, _) = struct.unpack_from(
          OSXMemory.format_efimemoryrange, mmap, x * desc_size)
      if seg_type in OSXMemory.valid_memory_types:
        result.append((start, pages * OSXMemory.page_size))

    return result

  def _ReadRandom(self, offset, length):
    self.fd.seek(offset)
    return self.fd.read(length)

if "linux" in sys.platform:
  vfs.VFS_HANDLERS[rdfvalue.PathSpec.PathType.MEMORY] = LinuxMemory

elif "win32" in sys.platform:
  vfs.VFS_HANDLERS[rdfvalue.PathSpec.PathType.MEMORY] = WindowsMemory

elif "darwin" in sys.platform:
  vfs.VFS_HANDLERS[rdfvalue.PathSpec.PathType.MEMORY] = OSXMemory
