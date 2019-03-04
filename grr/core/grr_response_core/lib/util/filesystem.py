#!/usr/bin/env python
"""A module with filesystem-related utility functions and classes."""
from __future__ import absolute_import
from __future__ import division

from __future__ import unicode_literals

import array
import os
import platform
import stat

from typing import Dict
from typing import NamedTuple
from typing import Text

from grr_response_core.lib.util import compatibility
from grr_response_core.lib.util import precondition


class Stat(object):
  """A wrapper around standard `os.[l]stat` function.

  The standard API for using `stat` results is very clunky and unpythonic.
  This is an attempt to create a more familiar and consistent interface to make
  the code look cleaner.

  Moreover, standard `stat` does not properly support extended flags - even
  though the documentation mentions that `stat.st_flags` should work on macOS
  and Linux it works only on macOS and raises an error on Linux (and Windows).
  This class handles that and fetches these flags lazily (as it can be costly
  operation on Linux).
  """

  @classmethod
  def FromPath(cls, path, follow_symlink = True):
    """Returns stat information about the given OS path, calling os.[l]stat.

    Args:
      path: A path to perform `stat` on.
      follow_symlink: True if `stat` of a symlink should be returned instead of
        a file that it points to. For non-symlinks this setting has no effect.

    Returns:
      Stat instance, with information about the given path.
    """
    # Note that we do not add type assertion for `path` here. The reason is that
    # many of the existing system calls (e.g. `os.listdir`) return results as
    # bytestrings in Python 2. This is fine because it also means that they also
    # accept bytestring paths as arguments in Python 2 (e.g. `os.stat`). Having
    # consistent types in both versions is certainly desired but it might be too
    # much work for too little benefit.
    precondition.AssertType(follow_symlink, bool)

    if follow_symlink:
      stat_obj = os.stat(path)
    else:
      stat_obj = os.lstat(path)

    return cls(path=path, stat_obj=stat_obj)

  def __init__(self, path, stat_obj):
    """Wrap an existing stat result in a `filesystem.Stat` instance.

    Args:
      path: the path of `stat_obj`.
      stat_obj: an instance of os.stat_result with information about `path`.
    """
    self._path = path
    self._stat = stat_obj
    self._flags_linux = None
    self._flags_osx = None

  def GetRaw(self):
    return self._stat

  def GetPath(self):
    return self._path

  def GetLinuxFlags(self):
    if self._flags_linux is None:
      self._flags_linux = self._FetchLinuxFlags()
    return self._flags_linux

  def GetOsxFlags(self):
    if self._flags_osx is None:
      self._flags_osx = self._FetchOsxFlags()
    return self._flags_osx

  def GetSize(self):
    return self._stat.st_size

  def GetAccessTime(self):
    return int(self._stat.st_atime)

  def GetModificationTime(self):
    return int(self._stat.st_mtime)

  def GetChangeTime(self):
    return int(self._stat.st_ctime)

  def GetDevice(self):
    return self._stat.st_dev

  def IsDirectory(self):
    return stat.S_ISDIR(self._stat.st_mode)

  def IsRegular(self):
    return stat.S_ISREG(self._stat.st_mode)

  def IsSocket(self):
    return stat.S_ISSOCK(self._stat.st_mode)

  def IsSymlink(self):
    return stat.S_ISLNK(self._stat.st_mode)

  # http://manpages.courier-mta.org/htmlman2/ioctl_list.2.html
  FS_IOC_GETFLAGS = 0x80086601

  def _FetchLinuxFlags(self):
    """Fetches Linux extended file flags."""
    if platform.system() != "Linux":
      return 0

    # Since we open a file in the next step we do not want to open a symlink.
    # `lsattr` returns an error when trying to check flags of a symlink, so we
    # assume that symlinks cannot have them.
    if self.IsSymlink():
      return 0

    # Some files (e.g. sockets) cannot be opened. For these we do not really
    # care about extended flags (they should have none). `lsattr` does not seem
    # to support such cases anyway. It is also possible that a file has been
    # deleted (because this method is used lazily).
    try:
      fd = os.open(self._path, os.O_RDONLY)
    except (IOError, OSError):
      return 0

    try:
      # This import is Linux-specific.
      import fcntl  # pylint: disable=g-import-not-at-top
      # TODO: On Python 2.7.6 `array.array` accepts only byte
      # strings as an argument. On Python 2.7.12 and 2.7.13 unicodes are
      # supported as well. On Python 3, only unicode strings are supported. This
      # is why, as a temporary hack, we wrap the literal with `str` call that
      # will convert it to whatever is the default on given Python version. This
      # should be changed to raw literal once support for Python 2 is dropped.
      buf = array.array(compatibility.NativeStr("l"), [0])
      # TODO(user):pytype: incorrect type spec for fcntl.ioctl
      # pytype: disable=wrong-arg-types
      fcntl.ioctl(fd, self.FS_IOC_GETFLAGS, buf)
      # pytype: enable=wrong-arg-types
      return buf[0]
    except (IOError, OSError):
      # File system does not support extended attributes.
      return 0
    finally:
      os.close(fd)

  def _FetchOsxFlags(self):
    """Fetches macOS extended file flags."""
    if platform.system() != "Darwin":
      return 0

    return self._stat.st_flags  # pytype: disable=attribute-error


class StatCache(object):
  """An utility class for avoiding unnecessary syscalls to `[l]stat`.

  This class is useful in situations where manual bookkeeping of stat results
  in order to prevent extra system calls becomes tedious and complicates control
  flow. This class makes sure that no unnecessary system calls are made and is
  smart enough to cache symlink results when a file is not a symlink.
  """

  # TODO(hanuszczak): https://github.com/python/typeshed/issues/2761
  # pytype: disable=wrong-arg-types
  _Key = NamedTuple("_Key", (("path", Text), ("follow_symlink", bool)))  # pylint: disable=invalid-name

  # pytype: enable=wrong-arg-types

  def __init__(self):
    self._cache = {}  # type: Dict[StatCache._Key, Stat]

  def Get(self, path, follow_symlink = True):
    """Stats given file or returns a cached result if available.

    Args:
      path: A path to the file to perform `stat` on.
      follow_symlink: True if `stat` of a symlink should be returned instead of
        a file that it points to. For non-symlinks this setting has no effect.

    Returns:
      `Stat` object corresponding to the given path.
    """
    key = self._Key(path=path, follow_symlink=follow_symlink)
    try:
      return self._cache[key]
    except KeyError:
      value = Stat.FromPath(path, follow_symlink=follow_symlink)
      self._cache[key] = value

      # If we are not following symlinks and the file is a not symlink then
      # the stat result for this file stays the same even if we want to follow
      # symlinks.
      if not follow_symlink and not value.IsSymlink():
        self._cache[self._Key(path=path, follow_symlink=True)] = value

      return value
