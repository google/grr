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

"""Implement low level disk access using the sleuthkit."""


import logging
import os
import stat
import time

#TODO(user): Fix pytsk so this can go away.
try:
  import pytsk3
except ImportError:
  import pytsk3

from grr.client import vfs
from grr.lib import utils
from grr.proto import jobs_pb2


DEVICE_CACHE = {}


class MyImgInfo(pytsk3.Img_Info):
  """An Img_Info class using the regular python file handling."""

  def __init__(self, filename):
    pytsk3.Img_Info.__init__(self)
    self.fd = open(filename, "rb")

  def read(self, offset, length):
    self.fd.seek(offset)
    return self.fd.read(length)

  def get_size(self):
    # Windows is unable to report the true size of the raw device and allows
    # arbitrary reading past the end - so we lie here to force tsk to read it
    # anyway
    return long(1e12)


class TSKFile(vfs.AbstractFileHandler):
  """Read a regular file."""

  supported_pathtype = jobs_pb2.Path.TSK

  # A mapping to encode TSK types to a stat.st_mode
  FILE_TYPE_LOOKUP = {
      pytsk3.TSK_FS_NAME_TYPE_UNDEF: 0,
      pytsk3.TSK_FS_NAME_TYPE_FIFO: stat.S_IFIFO,
      pytsk3.TSK_FS_NAME_TYPE_CHR: stat.S_IFCHR,
      pytsk3.TSK_FS_NAME_TYPE_DIR: stat.S_IFDIR,
      pytsk3.TSK_FS_NAME_TYPE_BLK: stat.S_IFBLK,
      pytsk3.TSK_FS_NAME_TYPE_REG: stat.S_IFREG,
      pytsk3.TSK_FS_NAME_TYPE_LNK: stat.S_IFLNK,
      pytsk3.TSK_FS_NAME_TYPE_SOCK: stat.S_IFSOCK,
      }

  META_TYPE_LOOKUP = {
      pytsk3.TSK_FS_META_TYPE_BLK: 0,
      pytsk3.TSK_FS_META_TYPE_CHR: stat.S_IFCHR,
      pytsk3.TSK_FS_META_TYPE_DIR: stat.S_IFDIR,
      pytsk3.TSK_FS_META_TYPE_FIFO: stat.S_IFIFO,
      pytsk3.TSK_FS_META_TYPE_LNK: stat.S_IFLNK,
      pytsk3.TSK_FS_META_TYPE_REG: stat.S_IFREG,
      pytsk3.TSK_FS_META_TYPE_SOCK: stat.S_IFSOCK,
      }

  CACHE_EXPIRY = 60 * 10  # 10 minutes.

  def __init__(self, pathspec):

    self.device, self.path = pathspec.device, pathspec.path
    self.device = self.device.rstrip("\\")
    self.request = pathspec

    if not self.device: raise IOError("No block device")

    # Now try to open the block device as a filesystem
    try:
      # Should we cache these to prevent potential file descriptor
      # leaks?
      self.fs = self._GetFSInfo(self.device)

      # Normalise the path casing
      self.path = self.NormaliseCase(self.path)
      self.request.path = self.path

      # Does the filename exist in the image?
      self.fd = self._OpenFd()
      self.size = self.fd.info.meta.size

    except RuntimeError, e:
      raise IOError(e)

  def BestCandidate(self, test_path, component):
    """List the test_path to find the case insensitive filename of component."""
    # Coerce to utf8
    test_path = utils.SmartStr(test_path)
    file_listing = set()
    for f in self.fs.open_dir(test_path):
      # TSK only deals with utf8 strings, but path components are always unicode
      # objects - so we convert to unicode as soon as we receive data from
      # TSK. Prefer to compare unicode objects to guarantee they are normalized.
      file_listing.add(utils.SmartUnicode(f.info.name.name))

    # First try the exact match
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
    path_components = [x for x in normalized_path.split("/") if x]

    # The drive letter
    result = ""

    for component in path_components:
      component = self.BestCandidate(result, component)
      result += "/" + component

    return result

  def _GetFSInfo(self, device):
    """Get a MyImgInfo object via the cache."""
    expiry = time.time() - self.CACHE_EXPIRY
    if device in DEVICE_CACHE and DEVICE_CACHE[device][0] > expiry:
      return DEVICE_CACHE[device][1]
    else:
      logging.debug("Sleuthkit cache miss for device %s", device)
      img = MyImgInfo(device)
      # Note we need img to stay around so we cache it as well.
      DEVICE_CACHE[device] = (time.time(), pytsk3.FS_Info(img), img)
      return DEVICE_CACHE[device][1]

  def _OpenFd(self):
    fd = self.fs.open(self.path.encode("utf8"))

    return fd

  def MakeStatResponse(self, directory, info):
    """Given a TSK info object make a StatResponse."""
    response = jobs_pb2.StatResponse()
    meta = info.meta
    if meta:
      response.st_ino = meta.addr
      for attribute in "mode nlink uid gid size atime mtime ctime".split():
        try:
          value = int(getattr(meta, attribute))
          if value < 0: value &= 0xFFFFFFFF

          setattr(response, "st_%s" % attribute, value)
        except AttributeError: pass

    name = info.name
    if name:
      response.pathspec.CopyFrom(self.request)
      response.pathspec.path = "/".join((directory,
                                         utils.SmartUnicode(name.name)))

      # Encode the type onto the st_mode response
      response.st_mode |= self.FILE_TYPE_LOOKUP.get(int(name.type), 0)

    if meta:
      # What if the types are different? What to do here?
      response.st_mode |= self.META_TYPE_LOOKUP.get(int(meta.type), 0)

    return response

  def Read(self, length):
    available = min(self.size - self.offset, length)
    if available > 0:
      data = self.fd.read_random(self.offset, available)
      self.offset += len(data)

      return data
    return ""

  def Stat(self):
    """Return a stat of the file."""
    return self.MakeStatResponse(os.path.dirname(self.path), self.fd.info)

  def ListFiles(self):
    """List all the files in the directory."""
    # TODO(user): not sure what we should do here. On my test system,
    # info.meta.type is an object.
    if (self.fd.info.meta and
        (self.fd.info.meta.type == pytsk3.TSK_FS_META_TYPE_DIR or
         type(self.fd.info.meta.type) == pytsk3.TSK_FS_META_TYPE_ENUM)):
      dir_fd = self.fs.open_dir(utils.SmartStr(self.path))

      for f in dir_fd:
        try:
          name = f.info.name.name
          # Drop these useless entries.
          if name not in [".", ".."]:
            yield self.MakeStatResponse(self.path, f.info)
        except AttributeError: pass
    else:
      raise IOError("%s is not a directory" % self.path)
