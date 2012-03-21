#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

# Copyright 2011 Google Inc.
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

"""Linux specific utils."""


import os
import time

from grr.client import client_config
from grr.lib import utils
from grr.proto import jobs_pb2


# TODO(user): Find reliable ways to do this for different OSes
def LinFindProxies():
  return client_config.PROXY_SERVERS

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
    data = "\n".join([open(x).read() for x in ["/proc/mounts", "/etc/mtab"]])

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


def LinGetRawDevice(path):
  """Resolve the raw device that contains the path."""
  device_map = GetMountpoints()

  path = utils.SmartUnicode(path)
  mount_point = path = utils.NormalizePath(path, "/")

  result = jobs_pb2.Path()
  result.pathtype = jobs_pb2.Path.OS

  # Assign the most specific mount point to the result
  while mount_point:
    try:
      result.path, fs_type = device_map[mount_point]
      if fs_type in ["ext2", "ext3", "ext4", "vfat", "ntfs"]:
        # These are read filesystems
        result.pathtype = jobs_pb2.Path.OS
      else:
        result.pathtype = jobs_pb2.Path.UNKNOWN

      # Drop the mount point
      path = utils.NormalizePath(path[len(mount_point):])
      result.mount_point = mount_point

      return result, path
    except KeyError:
      mount_point = os.path.dirname(mount_point)


def CanonicalPathToLocalPath(path):
  """Linux uses a normal path."""
  return utils.NormalizePath(path)


def LocalPathToCanonicalPath(path):
  """Linux uses a normal path."""
  return utils.NormalizePath(path)
