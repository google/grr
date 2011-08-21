#!/usr/bin/env python

# Copyright 2010 Google Inc.
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

"""Implements VFSHandlers for files on the client."""

import os

from grr.client import vfs
from grr.lib import utils
from grr.proto import jobs_pb2


def MakeStatResponse(st, request):
  """Creates a StatResponse proto."""
  response = jobs_pb2.StatResponse()

  # Now fill in the stat value
  for attr in ["st_mode",
               "st_ino",
               "st_dev",
               "st_nlink",
               "st_uid",
               "st_gid",
               "st_size",
               "st_atime",
               "st_mtime",
               "st_ctime",
               "st_blocks",
               "st_blksize",
               "st_rdev"]:
    try:
      value = long(getattr(st, attr))
      if value < 0: value &= 0xFFFFFFFF

      setattr(response, attr, value)
    except AttributeError:
      pass

  response.pathspec.CopyFrom(request)

  return response


class File(vfs.AbstractFileHandler):
  """Read a regular file."""

  supported_pathtype = jobs_pb2.Path.OS

  def __init__(self, pathspec):
    # Parts are already normalized, this is guaranteed to work
    self.path = pathspec.mountpoint + pathspec.path

    self.request = pathspec

    # Normalize the path casing if needed
    self.path = self.NormaliseCase(self.path).lstrip("\\")

    self.request.mountpoint = ""
    self.request.path = self.path

    # This sometimes raises
    try:
      self.fd = open(self.path, "rb")
    except UnicodeEncodeError, e:
      raise IOError(str(e))

    # Work out how large the file is
    self.fd.seek(0, 2)
    self.size = self.fd.tell()

  def _BestCandidate(self, test_path, component):
    """List the test_path to find the case insensitive filename of component."""
    try:
      file_listing = set(os.listdir(test_path + "/"))
    except OSError:
      return component

    # First try an exact match
    if component in file_listing:
      return component

    # Now try to match lower case
    lower_component = component.lower()
    for x in file_listing:
      if lower_component == x.lower(): return x

    # We dont know what the user meant. Just pass the original component
    # along.
    return component

  def NormaliseCase(self, path):
    """Returns a normalized form of the path."""
    # This removes possible directory traversal
    normalized_path = utils.NormalizePath(path.replace("\\", "/")).strip()
    drive, normalized_path = os.path.splitdrive(normalized_path)

    path_components = [x for x in normalized_path.split("/") if x]

    # The drive letter
    result = drive
    for component in path_components:
      component = self._BestCandidate(result, component)
      result += os.path.sep + component

    return result

  def Read(self, length):
    self.fd.seek(self.offset)
    data = self.fd.read(length)
    self.offset += len(data)

    return data

  def Stat(self, path=None):
    """Return a stat of the file."""
    st = os.stat(path or self.path)
    return MakeStatResponse(st, self.request)

  def Close(self):
    self.fd.close()


class Directory(File):
  """List a local directory."""

  def __init__(self, pathspec):
    # Parts are already normalized, this is guaranteed to work
    self.path = pathspec.mountpoint + pathspec.path
    self.request = pathspec

    try:
      self.files = os.listdir(self.path)
      # Some filesystems do not support unicode:
    except UnicodeEncodeError:
      raise OSError()

  def ListFiles(self):
    """List all files in the dir."""
    for path in self.files:
      try:
        response = self.Stat(os.path.sep.join((self.path, path)))
        response.pathspec.CopyFrom(self.request)
        response.pathspec.path = utils.Join(response.pathspec.path,
                                            path)

        yield response
      except OSError:
        pass
