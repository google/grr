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

import logging
import os
import re
import sys

from grr.client import client_utils
from grr.client import vfs
from grr.lib import utils
from grr.proto import jobs_pb2


def MakeStatResponse(st, pathspec):
  """Creates a StatResponse proto."""
  response = jobs_pb2.StatResponse()

  if st is None:
    # Special case empty stat if we don't have a real value, e.g. we get Access
    # denied when stating a file. We still want to give back a value so we let
    # the defaults from the proto pass through.
    pass
  else:
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

  # Write the pathspec into the result stat proto.
  pathspec.ToProto(response.pathspec)

  return response


class File(vfs.VFSHandler):
  """Read a regular file."""

  supported_pathtype = jobs_pb2.Path.OS
  auto_register = True

  # The file descriptor of the OS file.
  fd = None
  files = None

  def __init__(self, base_fd, pathspec=None):
    super(File, self).__init__(base_fd, pathspec=pathspec)
    if base_fd is None:
      self.pathspec.Append(pathspec)

    # We can stack on another directory, which means we concatenate their
    # directory with ours.
    elif base_fd.IsDirectory():
      self.pathspec.last.path = utils.JoinPath(self.pathspec.last.path,
                                               pathspec.path)

    else:
      raise IOError("File handler can not be stacked on another handler.")

    self.path = self.pathspec.last.path

    # We can optionally apply a global offset to the file.
    self.file_offset = self.pathspec[0].offset
    self.pathspec.last.path_options = jobs_pb2.Path.CASE_LITERAL

    self.WindowsHacks()

    error = None
    # Pythonic way - duck typing. Is the handle a directory?
    try:
      if not self.files:
        self.files = os.listdir(
            client_utils.CanonicalPathToLocalPath(self.path + "/"))

    # Some filesystems do not support unicode properly
    except UnicodeEncodeError, e:
      raise IOError(str(e))
    except (IOError, OSError), e:
      self.files = []
      error = e

    # Ok, it's not. Is it a file then?
    try:
      self.fd = open(client_utils.CanonicalPathToLocalPath(self.path), "rb")

      # Work out how large the file is
      if self.size == 0:
        # TODO(user): This does not work on windows devices.
        self.fd.seek(0, 2)
        self.size = self.fd.tell() - self.file_offset

      error = None
    # Some filesystems do not support unicode properly
    except UnicodeEncodeError, e:
      raise IOError(str(e))

    except IOError, e:
      if error:
        error = e

    if error is not None:
      raise error

  def WindowsHacks(self):
    """Windows specific hacks to make the filesystem look normal."""
    if sys.platform == "win32":
      import win32api

      # Make the filesystem look like the topmost level are the drive letters.
      if self.path == "/":
        self.files = win32api.GetLogicalDriveStrings().split("\x00")
        # Remove empty strings and strip trailing backslashes.
        self.files = [drive.rstrip("\\") for drive in self.files if drive]
      # This regex will match the various windows devices.
      elif re.match(r"\\\\.\\[^\\]+\\$", self.path) is not None:
        # Special case windows devices cant seek to the end so just lie about
        # the size
        self.size = 0x7fffffffffffffff

        # Windows raw devices can be opened in two incompatible modes. With a
        # trailing \ they look like a directory, but without they are the raw
        # device. In GRR we only support opening devices in raw mode so ensure
        # that we never append a \ to raw device name.
        self.path = self.path.rstrip("\\")

  def ListNames(self):
    return self.files or []

  def Read(self, length):
    """Read from the file."""
    if self.fd is None:
      raise IOError("%s is not a file." % self.path)

    self.fd.seek(self.file_offset + self.offset)
    data = self.fd.read(length)
    self.offset += len(data)

    return data

  def Stat(self, path=None):
    """Return a stat of the file."""
    client_path = client_utils.CanonicalPathToLocalPath(
        path or self.path)
    try:
      st = os.stat(client_path)
    except IOError, e:
      logging.info("Failed to Stat %s. Err: %s", path or self.path, e)
      st = None

    result = MakeStatResponse(st, self.pathspec)

    # Is this a symlink? If so we need to note the real location of the file.
    try:
      result.symlink = os.readlink(client_path)
    except (OSError, AttributeError):
      pass

    return result

  def Close(self):
    if self.fd:
      self.fd.close()

  def ListFiles(self):
    """List all files in the dir."""
    if not self.IsDirectory():
      raise IOError("%s is not a directory." % self.path)

    for path in self.files:
      try:
        response = self.Stat(utils.JoinPath(self.path, path))
        pathspec = self.pathspec.Copy()
        pathspec.last.path = utils.JoinPath(pathspec.last.path, path)
        pathspec.ToProto(response.pathspec)

        yield response
      except OSError:
        pass

  def IsDirectory(self):
    return self.fd is None
