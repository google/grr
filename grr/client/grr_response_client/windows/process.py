#!/usr/bin/env python
"""A class to read process memory on Windows.

This code is based on the memorpy project:
https://github.com/n1nj4sec/memorpy
"""

import ctypes
from ctypes import windll
from ctypes import wintypes
import platform

from grr_response_client import process_error
from grr_response_core.lib.rdfvalues import memory as rdf_memory

kernel32 = windll.kernel32

# Windows structs and functions have their own naming scheme, so
# pylint: disable=invalid-name

IsWow64Process = None

if hasattr(kernel32, "IsWow64Process"):
  IsWow64Process = kernel32.IsWow64Process
  IsWow64Process.restype = ctypes.c_bool
  IsWow64Process.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_bool)]

PROCESS_VM_READ = 0x10
PROCESS_QUERY_INFORMATION = 0x400

PAGE_READONLY = 2
PAGE_READWRITE = 4
PAGE_WRITECOPY = 8
PAGE_EXECUTE = 16
PAGE_EXECUTE_READ = 32
PAGE_EXECUTE_READWRITE = 64
PAGE_EXECUTE_WRITECOPY = 128
PAGE_GUARD = 256
PAGE_NOCACHE = 512
PAGE_WRITECOMBINE = 1024

MEM_COMMIT = 4096
MEM_RESERVE = 8192
MEM_FREE = 65536


class SECURITY_DESCRIPTOR(ctypes.Structure):
  _fields_ = [
      ("SID", wintypes.DWORD),
      ("group", wintypes.DWORD),
      ("dacl", wintypes.DWORD),
      ("sacl", wintypes.DWORD),
      ("test", wintypes.DWORD),
  ]


PSECURITY_DESCRIPTOR = ctypes.POINTER(SECURITY_DESCRIPTOR)


class SYSTEM_INFO(ctypes.Structure):
  _fields_ = [
      ("wProcessorArchitecture", wintypes.WORD),
      ("wReserved", wintypes.WORD),
      ("dwPageSize", wintypes.DWORD),
      ("lpMinimumApplicationAddress", wintypes.LPVOID),
      ("lpMaximumApplicationAddress", wintypes.LPVOID),
      ("dwActiveProcessorMask", wintypes.WPARAM),
      ("dwNumberOfProcessors", wintypes.DWORD),
      ("dwProcessorType", wintypes.DWORD),
      ("dwAllocationGranularity", wintypes.DWORD),
      ("wProcessorLevel", wintypes.WORD),
      ("wProcessorRevision", wintypes.WORD),
  ]


class MEMORY_BASIC_INFORMATION(ctypes.Structure):
  _fields_ = [
      ("BaseAddress", ctypes.c_void_p),
      ("AllocationBase", ctypes.c_void_p),
      ("AllocationProtect", wintypes.DWORD),
      ("RegionSize", ctypes.c_size_t),
      ("State", wintypes.DWORD),
      ("Protect", wintypes.DWORD),
      ("Type", wintypes.DWORD),
  ]


CloseHandle = kernel32.CloseHandle
CloseHandle.argtypes = [ctypes.c_void_p]

ReadProcessMemory = kernel32.ReadProcessMemory
ReadProcessMemory.argtypes = [
    wintypes.HANDLE,
    wintypes.LPCVOID,
    wintypes.LPVOID,
    ctypes.c_size_t,
    ctypes.POINTER(ctypes.c_size_t),
]

VirtualQueryEx = kernel32.VirtualQueryEx
VirtualQueryEx.argtypes = [
    wintypes.HANDLE,
    wintypes.LPCVOID,
    ctypes.POINTER(MEMORY_BASIC_INFORMATION),
    ctypes.c_size_t,
]
VirtualQueryEx.restype = ctypes.c_size_t

# pylint: enable=invalid-name


class Process(object):
  """A class to read process memory on Windows."""

  def __init__(self, pid=None, handle=None):
    """Creates a process for reading memory."""
    super().__init__()
    if pid is None and handle is None:
      raise process_error.ProcessError("No pid or handle given.")
    if pid is not None:
      self.pid = int(pid)
    else:
      self.pid = None
    self._existing_handle = handle

  def __enter__(self):
    self.Open()

    return self

  def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
    self.Close()

  def Is64bit(self):
    """Returns true if this is a 64 bit process."""
    if "64" not in platform.machine():
      return False
    iswow64 = ctypes.c_bool(False)
    if IsWow64Process is None:
      return False
    if not IsWow64Process(self.h_process, ctypes.byref(iswow64)):
      raise process_error.ProcessError("Error while calling IsWow64Process.")
    return not iswow64.value

  def Open(self):
    """Opens the process for reading."""

    if self._existing_handle:
      self.h_process = self._existing_handle
    else:
      self.h_process = kernel32.OpenProcess(
          PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, 0, self.pid
      )
    if not self.h_process:
      raise process_error.ProcessError(
          "Failed to open process (pid %d)." % self.pid
      )

    if self.Is64bit():
      si = self.GetNativeSystemInfo()
      self.max_addr = si.lpMaximumApplicationAddress
    else:
      si = self.GetSystemInfo()
      self.max_addr = 2147418111

    self.min_addr = si.lpMinimumApplicationAddress

  def Close(self):
    """Relases all resources this instance is using."""
    if self.h_process is not None:
      if self.h_process == self._existing_handle:
        # Not owned by this instance.
        ret = 1
      else:
        ret = CloseHandle(self.h_process)
      if ret == 1:
        self.h_process = None
        self.pid = None

  def GetSystemInfo(self):
    si = SYSTEM_INFO()
    kernel32.GetSystemInfo(ctypes.byref(si))
    return si

  def GetNativeSystemInfo(self):
    si = SYSTEM_INFO()
    kernel32.GetNativeSystemInfo(ctypes.byref(si))
    return si

  def VirtualQueryEx(self, address):
    mbi = MEMORY_BASIC_INFORMATION()
    res = VirtualQueryEx(
        self.h_process, address, ctypes.byref(mbi), ctypes.sizeof(mbi)
    )
    if not res:
      raise process_error.ProcessError("Error VirtualQueryEx: 0x%08X" % address)
    return mbi

  def Regions(
      self,
      skip_special_regions=False,
      skip_executable_regions=False,
      skip_readonly_regions=False,
  ):
    """Returns an iterator over the readable regions for this process."""
    offset = self.min_addr

    while True:
      if offset >= self.max_addr:
        break
      mbi = self.VirtualQueryEx(offset)
      offset = mbi.BaseAddress
      chunk = mbi.RegionSize
      protect = mbi.Protect
      state = mbi.State

      region = rdf_memory.ProcessMemoryRegion(
          start=offset,
          size=mbi.RegionSize,
          is_readable=True,
          is_writable=bool(
              protect
              & (
                  PAGE_EXECUTE_READWRITE
                  | PAGE_READWRITE
                  | PAGE_EXECUTE_WRITECOPY
                  | PAGE_WRITECOPY
              )
          ),
          is_executable=bool(
              protect
              & (
                  PAGE_EXECUTE
                  | PAGE_EXECUTE_READ
                  | PAGE_EXECUTE_READWRITE
                  | PAGE_EXECUTE_WRITECOPY
              )
          ),
      )
      is_special = (
          protect & PAGE_NOCACHE
          or protect & PAGE_WRITECOMBINE
          or protect & PAGE_GUARD
      )

      offset += chunk

      if (
          state & MEM_FREE
          or state & MEM_RESERVE
          or (skip_special_regions and is_special)
          or (skip_executable_regions and region.is_executable)
          or (skip_readonly_regions and not region.is_writable)
      ):
        continue

      yield region

  def ReadBytes(self, address, num_bytes):
    """Reads at most num_bytes starting from offset <address>."""
    address = int(address)
    buf = ctypes.create_string_buffer(num_bytes)
    bytesread = ctypes.c_size_t(0)
    res = ReadProcessMemory(
        self.h_process, address, buf, num_bytes, ctypes.byref(bytesread)
    )
    if res == 0:
      err = ctypes.GetLastError()
      if err == 299:
        # Only part of ReadProcessMemory has been done, let's return it.
        return buf.raw[: bytesread.value]
      raise process_error.ProcessError("Error in ReadProcessMemory: %d" % err)

    return buf.raw[: bytesread.value]

  @property
  def serialized_file_descriptor(self) -> int:
    return self.h_process

  @classmethod
  def CreateFromSerializedFileDescriptor(
      cls, serialized_file_descriptor: int
  ) -> "Process":
    return Process(handle=serialized_file_descriptor)
