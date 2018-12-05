#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Linux specific utils."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import logging
import os
import time

from grr_response_client import client_utils_osx_linux
from grr_response_client.linux import process

from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import paths as rdf_paths

# Shared functions between macOS and Linux.
# pylint: disable=invalid-name
GetExtAttrs = client_utils_osx_linux.GetExtAttrs
CanonicalPathToLocalPath = client_utils_osx_linux.CanonicalPathToLocalPath
LocalPathToCanonicalPath = client_utils_osx_linux.LocalPathToCanonicalPath
NannyController = client_utils_osx_linux.NannyController
VerifyFileOwner = client_utils_osx_linux.VerifyFileOwner
TransactionLog = client_utils_osx_linux.TransactionLog

# pylint: enable=invalid-name


# TODO(user): Find a reliable way to do this for Linux.
def FindProxies():
  return []


MOUNTPOINT_CACHE = [0, None]


def GetMountpoints(data=None):
  """List all the filesystems mounted on the system."""
  expiry = 60  # 1 min

  insert_time = MOUNTPOINT_CACHE[0]
  if insert_time + expiry > time.time():
    return MOUNTPOINT_CACHE[1]

  devices = {}

  # Check all the mounted filesystems.
  if data is None:
    data = "\n".join(
        [open(x, "rb").read() for x in ["/proc/mounts", "/etc/mtab"]])

  for line in data.splitlines():
    try:
      device, mnt_point, fs_type, _ = line.split(" ", 3)
      mnt_point = os.path.normpath(mnt_point)

      # What if several devices are mounted on the same mount point?
      devices[mnt_point] = (device, fs_type)
    except ValueError:
      pass

  MOUNTPOINT_CACHE[0] = time.time()
  MOUNTPOINT_CACHE[1] = devices

  return devices


SUPPORTED_FILESYSTEMS = ["ext2", "ext3", "ext4", "vfat", "ntfs"]


def GetRawDevice(path):
  """Resolve the raw device that contains the path."""
  device_map = GetMountpoints()

  path = utils.SmartUnicode(path)
  mount_point = path = utils.NormalizePath(path, "/")

  result = rdf_paths.PathSpec(pathtype=rdf_paths.PathSpec.PathType.OS)

  # Assign the most specific mount point to the result
  while mount_point:
    try:
      result.path, fs_type = device_map[mount_point]
      if fs_type in SUPPORTED_FILESYSTEMS:
        # These are read filesystems
        result.pathtype = rdf_paths.PathSpec.PathType.OS
      else:
        logging.error(
            "Filesystem %s is not supported. Supported filesystems "
            "are %s", fs_type, SUPPORTED_FILESYSTEMS)
        result.pathtype = rdf_paths.PathSpec.PathType.UNSET

      # Drop the mount point
      path = utils.NormalizePath(path[len(mount_point):])
      result.mount_point = mount_point

      return result, path
    except KeyError:
      mount_point = os.path.dirname(mount_point)


def KeepAlive():
  # Not yet supported for Linux.
  pass


def OpenProcessForMemoryAccess(pid=None):
  return process.Process(pid=pid)


def MemoryRegions(proc, options):
  for start, length in proc.Regions(
      skip_executable_regions=options.skip_executable_regions,
      skip_mapped_files=options.skip_mapped_files,
      skip_readonly_regions=options.skip_readonly_regions,
      skip_shared_regions=options.skip_shared_regions):
    yield start, length
