#!/usr/bin/env python
"""A class to read process memory on Linux.

This code is based on the memorpy project:
https://github.com/n1nj4sec/memorpy
"""

import ctypes
import errno
import os
import re

from grr_response_client import process_error
from grr_response_core.lib.rdfvalues import memory as rdf_memory

libc = ctypes.CDLL("libc.so.6", use_errno=True)


def Errcheck(ret, func, args):
  del args
  if ret == -1:
    raise OSError(
        "Error in %s: %s"
        % (func.__name__, os.strerror(ctypes.get_errno() or errno.EPERM))
    )
  return ret


c_pid_t = ctypes.c_int32  # This assumes pid_t is int32_t

c_off64_t = ctypes.c_longlong

lseek64 = libc.lseek64
lseek64.argtypes = [ctypes.c_int, c_off64_t, ctypes.c_int]
lseek64.errcheck = Errcheck

open64 = libc.open64
open64.restype = ctypes.c_int
open64.argtypes = [ctypes.c_void_p, ctypes.c_int]
open64.errcheck = Errcheck

pread64 = libc.pread64
pread64.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.c_size_t, c_off64_t]
pread64.restype = ctypes.c_ssize_t
pread64.errcheck = Errcheck

c_close = libc.close
c_close.argtypes = [ctypes.c_int]
c_close.restype = ctypes.c_int


class Process(object):
  """A class to read process memory on Linux."""

  maps_re = re.compile(
      r"([0-9A-Fa-f]+)-([0-9A-Fa-f]+)\s+([-rwpsx]+)\s+"
      r"([0-9A-Fa-f]+)\s+([0-9A-Fa-f]+:[0-9A-Fa-f]+)\s+([0-9]+)\s*(.*)"
  )

  def __init__(self, pid=None, mem_fd=None):
    """Creates a process for reading memory."""
    super().__init__()
    if pid is None and mem_fd is None:
      raise process_error.ProcessError("No pid or mem_fd given.")
    self.pid = pid
    self._existing_mem_fd = mem_fd

    self.mem_file = None

  def Open(self):
    if self.pid is not None:
      self._OpenPid()
    else:
      self._OpenMemFd()

  def _OpenPid(self):
    path = "/proc/{}/mem".format(self.pid)
    cpath = ctypes.create_string_buffer(path.encode("utf-8"))
    try:
      self.mem_file = open64(ctypes.byref(cpath), os.O_RDONLY)
    except OSError as e:
      raise process_error.ProcessError(e)

  def _OpenMemFd(self):
    self.mem_file = os.dup(self._existing_mem_fd)

  def Close(self):
    if self.mem_file:
      c_close(self.mem_file)
      self.mem_file = None

  def __enter__(self):
    self.Open()
    return self

  def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
    self.Close()

  def Regions(
      self,
      skip_mapped_files=False,
      skip_shared_regions=False,
      skip_executable_regions=False,
      skip_readonly_regions=False,
  ):
    """Returns an iterator over the readable regions for this process."""
    try:
      maps_file = open("/proc/" + str(self.pid) + "/maps", "r")
    except OSError as e:
      raise process_error.ProcessError(e)

    with maps_file:
      for line in maps_file:
        m = self.maps_re.match(line)
        if not m:
          continue
        start = int(m.group(1), 16)
        end = int(m.group(2), 16)
        region_protec = m.group(3)
        inode = int(m.group(6))

        is_writable = "w" in region_protec
        is_executable = "x" in region_protec

        if "r" in region_protec:
          if skip_mapped_files and inode != 0:
            continue
          if skip_shared_regions and "s" in region_protec:
            continue
          if skip_executable_regions and is_executable:
            continue
          if skip_readonly_regions and not is_writable:
            continue

          yield rdf_memory.ProcessMemoryRegion(
              start=start,
              size=end - start,
              is_readable=True,
              is_writable=is_writable,
              is_executable=is_executable,
          )

  def ReadBytes(self, address, num_bytes):
    lseek64(self.mem_file, address, os.SEEK_SET)
    try:
      return os.read(self.mem_file, num_bytes)
    except OSError:
      return ""

  @property
  def serialized_file_descriptor(self) -> int:
    return self.mem_file

  @classmethod
  def CreateFromSerializedFileDescriptor(
      cls,
      serialized_file_descriptor: int,
  ) -> "Process":
    return Process(mem_fd=serialized_file_descriptor)
