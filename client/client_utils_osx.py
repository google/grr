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

"""OSX specific utils."""


from grr.client import client_utils_linux
from grr.client.client_actions.osx import osx


# TODO(user): Find reliable ways to do this for different OSes
def OSXFindProxies():
  return None


def OSXGetMountpoints():
  """List all the filesystems mounted on the system."""
  devices = {}

  for filesys in osx.GetFileSystems():
    devices.setdefault(filesys.f_mntfromname, []).append(filesys.f_mntonname)

  return devices


def OSXSplitPathspec(pathspec):
  """Splits a given path into (device, mountpoint, remaining path).

  Examples:

  Let's say "/dev/disk0s1" is mounted on "/", then

  /mnt/data/directory/file.txt is split into
  (device="/dev/disk0s1", mountpoint="/", path="mnt/data/directory/file.txt")

  and

  /dev/disk0s1/home/test/ is split into ("/dev/disk0s1", "/", "home/test/").

  After the split, mountpoint and path can always be concatenated
  to obtain a valid os file path.

  Args:
    pathspec: Path specification to be split.

  Returns:
    Pathspec split into device, mountpoint, and remaining path.

  Raises:
    IOError: Path was not found on any mounted device.

  """

  # Splitting the pathspec is exactly the same as on Linux, we just
  # have use the OSX GetMountpoints function.

  return client_utils_linux.LinSplitPathspec(pathspec, OSXGetMountpoints)
