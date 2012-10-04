#!/usr/bin/env python
# Copyright 2012 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""VFS Handler which provides access to the raw physical memory.

Memory access is provided by use of a special driver. Note that it is preferred
to use this VFS handler rather than directly access the raw handler since this
handler protects the system from access unmapped memory regions such as DMA
regions. It is always safe to access all of memory using this handler.
"""


import struct
import sys

from grr.client import vfs
from grr.lib import utils
from grr.proto import jobs_pb2


class MemoryVFS(vfs.VFSHandler):
  """A base class for memory drivers."""

  @classmethod
  def Open(cls, base_fd, component, pathspec=None):
    _ = pathspec
    return cls(base_fd, pathspec=component)

  def IsDirectory(self):
    return False

  def Stat(self):
    result = jobs_pb2.StatResponse(st_size=self.size)
    self.pathspec.ToProto(result.pathspec)

    return result

if "linux" in sys.platform:

  class LinuxMemory(MemoryVFS):
    """A Linux memory VFS driver."""

    supported_pathtype = jobs_pb2.Path.MEMORY
    auto_register = True

    def __init__(self, base_fd, pathspec=None):
      """Open the raw memory image.

      Args:
        base_fd: The file like object we read this component from.
        pathspec: An optional pathspec to open directly.
      Raises:
        IOError: If the file can not be opened.
      """
      super(LinuxMemory, self).__init__(base_fd, pathspec=pathspec)
      if self.base_fd is not None:
        raise IOError("Memory driver must be a top level.")

      # The linux memory acquisition driver is very easy to use.
      self.fd = open(pathspec.path, "rb")

    def Read(self, length):
      return self.fd.read(length)

    def Seek(self, offset, whence=0):
      self.fd.seek(offset, whence)

    def Tell(self):
      return self.fd.tell()

# The windows driver has special requirements.
elif sys.platform.startswith("win"):
  import win32file

  from grr.client.client_actions.windows import windows

  class WindowsMemory(MemoryVFS):
    """Read the raw memory."""
    supported_pathtype = jobs_pb2.Path.MEMORY
    auto_register = True

    # This is the dtb if available
    cr3 = None

    def __init__(self, base_fd, pathspec=None):
      """Open the raw memory image.

      Args:
        base_fd: The file like object we read this component from.
        pathspec: An optional pathspec to open directly.
      Raises:
        IOError: If the file can not be opened.
      """
      super(WindowsMemory, self).__init__(base_fd, pathspec=pathspec)
      if self.base_fd is not None:
        raise IOError("Memory driver must be a top level.")

      self.pathspec = utils.Pathspec(pathspec)

      # We need to use win32 api to open the device.
      self.fd = win32file.CreateFile(
          pathspec.path,
          win32file.GENERIC_READ | win32file.GENERIC_WRITE,
          win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE,
          None,
          win32file.OPEN_EXISTING,
          win32file.FILE_ATTRIBUTE_NORMAL,
          None)

      # Obtain the valid memory runs
      data = win32file.DeviceIoControl(
          self.fd, windows.INFO_IOCTRL, "", 1024, None)
      fmt_string = "QQl"
      self.cr3, _, number_of_runs = struct.unpack_from(fmt_string, data)

      offset = struct.calcsize(fmt_string)
      self.runs = []
      self.size = 0
      for x in range(number_of_runs):
        start, length = struct.unpack_from("QQ", data, x * 16 + offset)
        if length == 0: break

        self.runs.append((start, length))
        self.size = start + length

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
        if self.offset >= last_end and self.offset < start:
          # Zero pad it
          return "\x00" * min(length, start - self.offset)

        last_end = end = start + run_length
        # File pointer falls within a valid range, just read from the device.
        if self.offset >= start and self.offset < end:
          to_read = min(length, end - self.offset)
          win32file.SetFilePointer(self.fd, self.offset, 0)

          _, data = win32file.ReadFile(self.fd, to_read)

          return data

# Alas no macosx driver at present :-(
