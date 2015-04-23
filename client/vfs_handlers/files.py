#!/usr/bin/env python
# Copyright 2010 Google Inc. All Rights Reserved.
"""Implements VFSHandlers for files on the client."""

import logging
import os
import platform
import re
import sys
import threading

from grr.client import client_utils
from grr.client import vfs
from grr.lib import rdfvalue
from grr.lib import utils


# File handles are cached here. They expire after a couple minutes so
# we don't keep files locked on the client.
FILE_HANDLE_CACHE = utils.TimeBasedCache(max_age=300)


class LockedFileHandle(object):
  """An object which encapsulates access to a file."""

  def __init__(self, filename):
    self.lock = threading.RLock()
    self.fd = open(filename, "rb")
    self.filename = filename

  def Seek(self, offset, whence=0):
    self.fd.seek(offset, whence)

  def Read(self, length):
    return self.fd.read(length)

  def Tell(self):
    return self.fd.tell()

  def Close(self):
    with self.lock:
      self.fd.close()


class FileHandleManager(object):
  """An exclusive accesssor for a filehandle."""

  def __init__(self, filename):
    self.filename = filename

  def __enter__(self):
    try:
      self.fd = FILE_HANDLE_CACHE.Get(self.filename)
    except KeyError:
      self.fd = LockedFileHandle(self.filename)
      FILE_HANDLE_CACHE.Put(self.filename, self.fd)

    # Wait for exclusive access to this file handle.
    self.fd.lock.acquire()

    return self.fd

  def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
    self.fd.lock.release()


def MakeStatResponse(st, pathspec):
  """Creates a StatEntry."""
  response = rdfvalue.StatEntry(pathspec=pathspec)

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

  return response


class File(vfs.VFSHandler):
  """Read a regular file."""

  supported_pathtype = rdfvalue.PathSpec.PathType.OS
  auto_register = True

  # The file descriptor of the OS file.
  fd = None
  files = None

  # Directories do not have a size.
  size = None

  # On windows reading devices must have an alignment.
  alignment = 1
  file_offset = 0

  def __init__(self, base_fd, pathspec=None, progress_callback=None):
    super(File, self).__init__(base_fd, pathspec=pathspec,
                               progress_callback=progress_callback)
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
    if self.pathspec[0].HasField("offset"):
      self.file_offset = self.pathspec[0].offset

    self.pathspec.last.path_options = rdfvalue.PathSpec.Options.CASE_LITERAL

    self.WindowsHacks()
    self.filename = client_utils.CanonicalPathToLocalPath(self.path)

    error = None
    # Pythonic way - duck typing. Is the handle a directory?
    try:
      if not self.files:
        # Note that the encoding of local path is system specific
        local_path = client_utils.CanonicalPathToLocalPath(self.path + "/")
        self.files = [utils.SmartUnicode(entry) for entry in
                      os.listdir(local_path)]
    # Some filesystems do not support unicode properly
    except UnicodeEncodeError as e:
      raise IOError(str(e))
    except (IOError, OSError) as e:
      self.files = []
      error = e

    # Ok, it's not. Is it a file then?
    try:
      with FileHandleManager(self.filename) as fd:

        # Work out how large the file is
        if self.size is None:
          fd.Seek(0, 2)
          self.size = fd.Tell() - self.file_offset

      error = None
    # Some filesystems do not support unicode properly
    except UnicodeEncodeError as e:
      raise IOError(str(e))

    except IOError as e:
      if error:
        error = e

    if error is not None:
      raise error  # pylint: disable=raising-bad-type

  def WindowsHacks(self):
    """Windows specific hacks to make the filesystem look normal."""
    if sys.platform == "win32":
      import win32api  # pylint: disable=g-import-not-at-top

      # Make the filesystem look like the topmost level are the drive letters.
      if self.path == "/":
        self.files = win32api.GetLogicalDriveStrings().split("\x00")
        # Remove empty strings and strip trailing backslashes.
        self.files = [drive.rstrip("\\") for drive in self.files if drive]

      # This regex will match the various windows devices. Raw hard disk devices
      # must be considered files, however in windows, if we try to list them as
      # directories this also works. Since the code above distinguished between
      # files and directories using the file listing property, we must force
      # treating raw devices as files.
      elif re.match(r"/*\\\\.\\[^\\]+\\?$", self.path) is not None:
        # Special case windows devices cant seek to the end so just lie about
        # the size
        self.size = 0x7fffffffffffffff

        # Windows raw devices can be opened in two incompatible modes. With a
        # trailing \ they look like a directory, but without they are the raw
        # device. In GRR we only support opening devices in raw mode so ensure
        # that we never append a \ to raw device name.
        self.path = self.path.rstrip("\\")

        # In windows raw devices must be accessed using sector alignment.
        self.alignment = 512

  def ListNames(self):
    return self.files or []

  def Read(self, length):
    """Read from the file."""
    if self.progress_callback:
      self.progress_callback()
    with FileHandleManager(self.filename) as fd:
      offset = self.file_offset + self.offset
      pre_padding = offset % self.alignment

      # Due to alignment we read some more data than we need to.
      aligned_offset = offset - pre_padding

      fd.Seek(aligned_offset)

      data = fd.Read(length + pre_padding)
      self.offset += len(data) - pre_padding

      return data[pre_padding:]

  def Stat(self, path=None):
    """Returns stat information of a specific path.

    Args:
      path: a Unicode string containing the path or None.
            If path is None the value in self.path is used.

    Returns:
      a StatResponse proto

    Raises:
      IOError when call to os.stat() fails
    """
    # Note that the encoding of local path is system specific
    local_path = client_utils.CanonicalPathToLocalPath(
        path or self.path)
    try:
      st = os.stat(local_path)
    except IOError as e:
      logging.info("Failed to Stat %s. Err: %s", path or self.path, e)
      st = None

    result = MakeStatResponse(st, self.pathspec)

    # Is this a symlink? If so we need to note the real location of the file.
    try:
      result.symlink = utils.SmartUnicode(os.readlink(local_path))
    except (OSError, AttributeError):
      pass

    return result

  def ListFiles(self):
    """List all files in the dir."""
    if not self.IsDirectory():
      raise IOError("%s is not a directory." % self.path)

    else:
      for path in self.files:
        try:
          response = self.Stat(utils.JoinPath(self.path, path))
          pathspec = self.pathspec.Copy()
          pathspec.last.path = utils.JoinPath(pathspec.last.path, path)
          response.pathspec = pathspec

          yield response
        except OSError:
          pass

  def IsDirectory(self):
    return self.size is None

  def StatFS(self, path=None):
    """Call os.statvfs for a given list of paths. OS X and Linux only.

    Note that a statvfs call for a network filesystem (e.g. NFS) that is
    unavailable, e.g. due to no network, will result in the call blocking.

    Args:
      path: a Unicode string containing the path or None.
            If path is None the value in self.path is used.
    Returns:
      posix.statvfs_result object
    Raises:
      RuntimeError: if called on windows
    """
    if platform.system() == "Windows":
      raise RuntimeError("os.statvfs not available on Windows")

    local_path = client_utils.CanonicalPathToLocalPath(
        path or self.path)

    return os.statvfs(local_path)

  def GetMountPoint(self, path=None):
    """Walk back from the path to find the mount point.

    Args:
      path: a Unicode string containing the path or None.
            If path is None the value in self.path is used.

    Returns:
      path string of the mount point
    """
    path = os.path.abspath(client_utils.CanonicalPathToLocalPath(
        path or self.path))

    while not os.path.ismount(path):
      path = os.path.dirname(path)

    return path
