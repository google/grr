#!/usr/bin/env python
"""Implements VFSHandlers for files on the client."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import logging
import os
import platform
import re
import sys
import threading

from grr_response_client import client_utils
from grr_response_client import vfs
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import paths as rdf_paths

# File handles are cached here. They expire after a couple minutes so
# we don't keep files locked on the client.
FILE_HANDLE_CACHE = utils.TimeBasedCache(max_age=300)


class LockedFileHandle(object):
  """An object which encapsulates access to a file."""

  def __init__(self, filename, mode="rb"):
    self.lock = threading.RLock()
    self.fd = open(filename, mode)
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
      self.fd = LockedFileHandle(self.filename, mode="rb")
      FILE_HANDLE_CACHE.Put(self.filename, self.fd)

    # Wait for exclusive access to this file handle.
    self.fd.lock.acquire()

    return self.fd

  def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
    self.fd.lock.release()


class File(vfs.VFSHandler):
  """Read a regular file."""

  supported_pathtype = rdf_paths.PathSpec.PathType.OS
  auto_register = True

  files = None

  # Directories do not have a size.
  size = None

  # On windows reading devices must have an alignment.
  alignment = 1
  file_offset = 0

  def __init__(self, base_fd, pathspec=None, progress_callback=None):
    super(File, self).__init__(
        base_fd, pathspec=pathspec, progress_callback=progress_callback)
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

    self.pathspec.last.path_options = rdf_paths.PathSpec.Options.CASE_LITERAL

    self.FileHacks()
    self.filename = client_utils.CanonicalPathToLocalPath(self.path)

    error = None
    # Pythonic way - duck typing. Is the handle a directory?
    try:
      if not self.files:
        # Note that the encoding of local path is system specific
        local_path = client_utils.CanonicalPathToLocalPath(self.path + "/")
        self.files = [
            utils.SmartUnicode(entry) for entry in os.listdir(local_path)
        ]
    # Some filesystems do not support unicode properly
    except UnicodeEncodeError as e:
      raise IOError(str(e))
    except (IOError, OSError) as e:
      self.files = []
      error = e

    # Ok, it's not. Is it a file then?
    try:
      with FileHandleManager(self.filename) as fd:

        if pathspec.last.HasField("file_size_override"):
          self.size = pathspec.last.file_size_override - self.file_offset
        else:
          # Work out how large the file is.
          if self.size is None:
            fd.Seek(0, 2)
            end = fd.Tell()
            if end == 0:
              # This file is not seekable, we just use the default.
              end = pathspec.last.file_size_override

            self.size = end - self.file_offset

      error = None
    # Some filesystems do not support unicode properly
    except UnicodeEncodeError as e:
      raise IOError(str(e))

    except IOError as e:
      if error:
        error = e

    if error is not None:
      raise error  # pylint: disable=raising-bad-type

  def FileHacks(self):
    """Hacks to make the filesystem look normal."""
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
    elif sys.platform == "darwin":
      # On Mac, raw disk devices are also not seekable to the end and have no
      # size so we use the same approach as on Windows.
      if re.match("/dev/r?disk.*", self.path):
        self.size = 0x7fffffffffffffff
        self.alignment = 512

  def _GetDepth(self, path):
    if path[0] != os.path.sep:
      raise RuntimeError("Relative paths aren't supported.")
    return len(re.findall(r"%s+[^%s]+" % (os.path.sep, os.path.sep), path))

  def _GetDevice(self, path):
    try:
      return utils.Stat(path).GetDevice()
    except (IOError, OSError) as error:
      logging.error("Failed to obtain device for '%s' (%s)", path, error)
      return None

  def ListNames(self):
    return self.files or []

  def Read(self, length=None):
    """Read from the file."""

    if self.progress_callback:
      self.progress_callback()

    available_to_read = max(0, (self.size or 0) - self.offset)
    if length is None:
      to_read = available_to_read
    else:
      to_read = min(length, available_to_read)

    with FileHandleManager(self.filename) as fd:
      offset = self.file_offset + self.offset
      pre_padding = offset % self.alignment

      # Due to alignment we read some more data than we need to.
      aligned_offset = offset - pre_padding

      fd.Seek(aligned_offset)

      data = fd.Read(to_read + pre_padding)
      self.offset += len(data) - pre_padding

      return data[pre_padding:]

  def Stat(self, ext_attrs=False):
    return self._Stat(self.path, ext_attrs=ext_attrs)

  def _Stat(self, path, ext_attrs=False):
    """Returns stat information of a specific path.

    Args:
      path: A unicode string containing the path.
      ext_attrs: Whether the call should also collect extended attributes.

    Returns:
      a StatResponse proto

    Raises:
      IOError when call to os.stat() fails
    """
    # Note that the encoding of local path is system specific
    local_path = client_utils.CanonicalPathToLocalPath(path)
    result = client_utils.StatEntryFromPath(
        local_path, self.pathspec, ext_attrs=ext_attrs)

    # Is this a symlink? If so we need to note the real location of the file.
    try:
      result.symlink = utils.SmartUnicode(os.readlink(local_path))
    except (OSError, AttributeError):
      pass

    return result

  def ListFiles(self, ext_attrs=False):
    """List all files in the dir."""
    if not self.IsDirectory():
      raise IOError("%s is not a directory." % self.path)

    for path in self.files:
      try:
        filepath = utils.JoinPath(self.path, path)
        response = self._Stat(filepath, ext_attrs=ext_attrs)
        pathspec = self.pathspec.Copy()
        pathspec.last.path = utils.JoinPath(pathspec.last.path, path)
        response.pathspec = pathspec

        yield response
      except OSError:
        pass

  def IsDirectory(self):
    return self.size is None

  def StatFS(self, path=None):
    """Call os.statvfs for a given list of rdf_paths. OS X and Linux only.

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

    local_path = client_utils.CanonicalPathToLocalPath(path or self.path)

    return os.statvfs(local_path)

  def GetMountPoint(self, path=None):
    """Walk back from the path to find the mount point.

    Args:
      path: a Unicode string containing the path or None.
            If path is None the value in self.path is used.

    Returns:
      path string of the mount point
    """
    path = os.path.abspath(
        client_utils.CanonicalPathToLocalPath(path or self.path))

    while not os.path.ismount(path):
      path = os.path.dirname(path)

    return path


class TempFile(File):
  """GRR temporary files on the client."""
  supported_pathtype = rdf_paths.PathSpec.PathType.TMPFILE
