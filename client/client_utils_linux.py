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
import stat

from grr.lib import utils
from grr.proto import jobs_pb2


# TODO(user): Find reliable ways to do this for different OSes
def LinFindProxies():
  return None


def GetMountpoints():
  #TODO(user): We should do some caching here...
  """List all the filesystems mounted on the system."""

  acceptable_filesystems = set(["ext2", "ext3", "ext4", "vfat", "ntfs"])

  devices = {}
  # For now we check all the mounted filesystems.
  for filename in ["/proc/mounts", "/etc/mtab"]:
    # This handles the case where the same filesystem is mounted on
    # multiple places.
    with open(filename) as fd:
      for line in fd:
        try:
          device, mnt_point, fs_type, _ = line.split(" ", 3)
          if fs_type in acceptable_filesystems:
            try:
              os.stat(device.encode("utf-8"))
            except OSError:
              continue
            try:
              if mnt_point not in devices[device]:
                devices[device].append(mnt_point)
            except KeyError:
              devices[device] = [mnt_point]
        except ValueError:
          pass

  return devices


def LinSplitPathspec(pathspec, getmountpoints=GetMountpoints):
  """Splits a given path into (device, mountpoint, remaining path).

  Examples:

  Let's say "/dev/sda1" is mounted on "/", then

  /mnt/data/directory/file.txt is split into
  (device="/dev/sda1", mountpoint="/", path="mnt/data/directory/file.txt")

  and

  /dev/sda1/home/test/ is split into ("/dev/sda1", "/", "home/test/").

  After the split, mountpoint and path can always be concatenated
  to obtain a valid os file path.

  Args:
    pathspec: Path specification to be split.
    getmountpoints: Function to retrieve the mountpoints on a system.

  Returns:
    Pathspec split into device, mountpoint, and remaining path.

  Raises:
    IOError: Path was not found on any mounted device.

  """

  if pathspec.pathtype == jobs_pb2.Path.REGISTRY:
    raise IOError("Unsupported pathtype (REGISTRY).")

  mountpoints = getmountpoints()

  path = pathspec.mountpoint + pathspec.path
  path = utils.SmartUnicode(path)
  path = utils.NormalizePath(path, "/")

  # Accept a path starting with a device.
  for device in mountpoints:
    if path.startswith(device):
      # Just give it any mountpoint of the specified device so
      # we can find the path using os functions later on.
      path = mountpoints[device][0] + path[len(device):]
      break

  candidates = []
  for device, mounts in mountpoints.items():
    for mountpoint in mounts:
      if path.startswith(mountpoint):
        candidates.append((device, mountpoint))

  if not candidates:
    raise IOError("No mountpoint for path: %s" % path)

  candidates.sort(key=lambda (d, m): len(m), reverse=True)

  dev, mp = candidates[0]
  tail = path[len(mp):]

  parts = mp.rstrip("/").split("/")
  tail_parts = tail.split("/")

  while tail_parts:
    parts.append(tail_parts.pop(0))

    img_path = "/".join(parts)

    try:
      # File names must be encoded.
      mode = os.stat(utils.SmartStr(img_path)).st_mode

      if (stat.S_ISBLK(mode) or stat.S_ISREG(mode)) and tail_parts:
        # We have found an image on disk.
        dev = img_path
        mp = img_path
        break
    except OSError:
      pass

  res = jobs_pb2.Path()
  res.pathtype = pathspec.pathtype
  res.device, res.mountpoint = dev, mp
  res.path = path[len(res.mountpoint):]

  return res
