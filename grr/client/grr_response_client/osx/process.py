#!/usr/bin/env python
"""A class to read process memory on macOS.

This code is based on the memorpy project:
https://github.com/n1nj4sec/memorpy

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import ctypes
import ctypes.util

from grr_response_client import process_error

libc = ctypes.CDLL(ctypes.util.find_library("c"))


# pylint:disable=invalid-name
class vm_region_submap_short_info_data_64(ctypes.Structure):
  _pack_ = 1
  _fields_ = [
      ("protection", ctypes.c_uint32),
      ("max_protection", ctypes.c_uint32),
      ("inheritance", ctypes.c_uint32),
      ("offset", ctypes.c_ulonglong),
      ("user_tag", ctypes.c_uint32),
      ("ref_count", ctypes.c_uint32),
      ("shadow_depth", ctypes.c_uint16),
      ("external_pager", ctypes.c_byte),
      ("share_mode", ctypes.c_byte),
      ("is_submap", ctypes.c_uint32),
      ("behavior", ctypes.c_uint32),
      ("object_id", ctypes.c_uint32),
      ("user_wired_count", ctypes.c_uint32),
  ]


# pylint: enable=invalid-name

submap_info_size = ctypes.sizeof(vm_region_submap_short_info_data_64) // 4

VM_PROT_READ = 1
VM_PROT_WRITE = 2
VM_PROT_EXECUTE = 4

SM_COW = 1
SM_PRIVATE = 2
SM_EMPTY = 3
SM_SHARED = 4
SM_TRUESHARED = 5
SM_PRIVATE_ALIASED = 6
SM_SHARED_ALIASED = 7


class Process(object):
  """A class to read process memory on macOS."""

  def __init__(self, pid=None):
    """Creates a process for reading memory."""
    super(Process, self).__init__()
    if pid is None:
      raise process_error.ProcessError("No pid given.")
    self.pid = pid

    self.task = None
    self.mytask = None
    self.Open()

  def __enter__(self):
    self.Open()
    return self

  def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
    pass

  def Close(self):
    pass

  def Open(self):
    self.task = ctypes.c_uint32()
    self.mytask = libc.mach_task_self()
    ret = libc.task_for_pid(self.mytask, ctypes.c_int(self.pid),
                            ctypes.pointer(self.task))
    if ret:
      if ret == 5:
        # Most likely this means access denied. This is not perfect
        # but there is no way to find out.
        raise process_error.ProcessError(
            "Access denied (task_for_pid returned 5).")

      raise process_error.ProcessError(
          "task_for_pid failed with error code : %s" % ret)

  def Regions(self,
              skip_executable_regions=False,
              skip_shared_regions=False,
              skip_readonly_regions=False):
    """Iterates over the readable regions for this process.

    We use mach_vm_region_recurse here to get a fine grained view of
    the process' memory space. The algorithm is that for some regions,
    the function returns is_submap=True which means that there are
    actually subregions that we need to examine by increasing the
    depth and calling the function again. For example, there are two
    regions, addresses 1000-2000 and 2000-3000 where 1000-2000 has two
    subregions, 1100-1200 and 1300-1400. In that case we would call:

    mvrr(address=0, depth=0)       -> (1000-2000, is_submap=True)
    mvrr(address=0, depth=1)       -> (1100-1200, is_submap=False)
    mvrr(address=1200, depth=1)    -> (1300-1400, is_submap=False)
    mvrr(address=1400, depth=1)    -> (2000-3000, is_submap=False)

    At this point, we know we went out of the original submap which
    ends at 2000. We need to recheck the region at 2000, it could be
    submap = True at depth 0 so we call

    mvrr(address=1400, depth=0)    -> (2000-3000, is_submap=False)

    Args:
      skip_executable_regions: Skips executable sections.
      skip_shared_regions: Skips shared sections. Includes mapped files.
      skip_readonly_regions: Skips readonly sections.

    Yields:
      Pairs (address, length) for each identified region.
    """

    address = ctypes.c_ulong(0)
    mapsize = ctypes.c_ulong(0)
    count = ctypes.c_uint32(submap_info_size)
    sub_info = vm_region_submap_short_info_data_64()
    depth = 0
    depth_end_addresses = {}

    while True:
      c_depth = ctypes.c_uint32(depth)

      r = libc.mach_vm_region_recurse(self.task, ctypes.pointer(address),
                                      ctypes.pointer(mapsize),
                                      ctypes.pointer(c_depth),
                                      ctypes.pointer(sub_info),
                                      ctypes.pointer(count))

      # If we get told "invalid address", we have crossed into kernel land...
      if r == 1:
        break

      if r != 0:
        raise process_error.ProcessError("Error in mach_vm_region, ret=%s" % r)

      if depth > 0 and address.value >= depth_end_addresses[depth]:
        del depth_end_addresses[depth]
        depth -= 1
        continue

      p = sub_info.protection
      if skip_executable_regions and p & VM_PROT_EXECUTE:
        address.value += mapsize.value
        continue

      if skip_shared_regions and sub_info.share_mode in [
          SM_COW, SM_SHARED, SM_TRUESHARED
      ]:
        address.value += mapsize.value
        continue

      if not p & VM_PROT_READ:
        address.value += mapsize.value
        continue

      writable = p & VM_PROT_WRITE
      if skip_readonly_regions and not writable:
        address.value += mapsize.value
        continue

      if sub_info.is_submap:
        depth += 1
        depth_end_addresses[depth] = address.value + mapsize.value
      else:
        yield address.value, mapsize.value
        address.value += mapsize.value

  def ReadBytes(self, address, num_bytes):
    """Reads at most num_bytes starting from offset <address>."""
    pdata = ctypes.c_void_p(0)
    data_cnt = ctypes.c_uint32(0)

    ret = libc.mach_vm_read(self.task, ctypes.c_ulonglong(address),
                            ctypes.c_longlong(num_bytes), ctypes.pointer(pdata),
                            ctypes.pointer(data_cnt))
    if ret:
      raise process_error.ProcessError("Error in mach_vm_read, ret=%s" % ret)
    buf = ctypes.string_at(pdata.value, data_cnt.value)
    libc.vm_deallocate(self.mytask, pdata, data_cnt)
    return buf
