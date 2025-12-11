#!/usr/bin/env python
"""A module with filesystem-related utility functions and classes."""

import array
import os
import platform
import stat
from typing import NamedTuple, Optional

from grr_response_core.lib.util import precondition


class Stat:
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
  def FromPath(cls, path: str, follow_symlink: bool = True) -> "Stat":
    """Returns stat information about the given OS path, calling os.[l]stat.

    Args:
      path: A path to perform `stat` on.
      follow_symlink: True if `stat` of a file that a symlink points to should
        be returned instead of the symlink itself. For non-symlinks this setting
        has no effect.

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

    try:
      target = os.readlink(path)
    # `os.readlink` raises `ValueError` on Windows and `OSError` on UNIX.
    except (OSError, ValueError):
      target = None

    return cls(path=path, stat_obj=stat_obj, symlink_target=target)

  def __init__(
      self,
      path: str,
      stat_obj: os.stat_result,
      symlink_target: Optional[str] = None,
  ) -> None:
    """Wrap an existing stat result in a `filesystem.Stat` instance.

    Args:
      path: the path of `stat_obj`.
      stat_obj: an instance of os.stat_result with information about `path`.
      symlink_target: Path of the original file that symlink refers to.
    """
    self._path = path
    self._stat = stat_obj
    self._symlink_target = symlink_target
    self._flags_linux = None
    self._flags_osx = None

  def GetRaw(self) -> os.stat_result:
    return self._stat

  def GetPath(self) -> str:
    return self._path

  def GetLinuxFlags(self) -> int:
    if self._flags_linux is None:
      self._flags_linux = self._FetchLinuxFlags()
    return self._flags_linux

  def GetOsxFlags(self) -> int:
    if self._flags_osx is None:
      self._flags_osx = self._FetchOsxFlags()
    return self._flags_osx

  def GetSize(self) -> int:
    return self._stat.st_size

  def GetAccessTime(self) -> int:
    # st_atime_ns is a higher-precision version of st_atime. Use it if it's
    # present.
    if self._stat.st_atime_ns is not None:
      return _NanosecondsToMicroseconds(self._stat.st_atime_ns)
    else:
      return _SecondsToMicroseconds(self._stat.st_atime.AsSecondsSinceEpoch())

  def GetModificationTime(self) -> int:
    # st_mtime_ns is a higher-precision version of st_mtime. Use it if it's
    # present.
    if self._stat.st_mtime_ns is not None:
      return _NanosecondsToMicroseconds(self._stat.st_mtime_ns)
    else:
      return _SecondsToMicroseconds(self._stat.st_mtime.AsSecondsSinceEpoch())

  def GetChangeTime(self) -> int:
    # st_ctime_ns is a higher-precision version of st_ctime. Use it if it's
    # present.
    if self._stat.st_ctime_ns is not None:
      return _NanosecondsToMicroseconds(self._stat.st_ctime_ns)
    else:
      return _SecondsToMicroseconds(self._stat.st_ctime.AsSecondsSinceEpoch())

  def GetDevice(self) -> int:
    return self._stat.st_dev

  def GetSymlinkTarget(self) -> Optional[str]:
    return self._symlink_target

  def IsDirectory(self) -> bool:
    return stat.S_ISDIR(self._stat.st_mode)

  def IsRegular(self) -> bool:
    return stat.S_ISREG(self._stat.st_mode)

  def IsSocket(self) -> bool:
    return stat.S_ISSOCK(self._stat.st_mode)

  def IsSymlink(self) -> bool:
    return stat.S_ISLNK(self._stat.st_mode)

  # http://manpages.courier-mta.org/htmlman2/ioctl_list.2.html
  FS_IOC_GETFLAGS = 0x80086601

  def _FetchLinuxFlags(self) -> int:
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

      buf = array.array("l", [0])
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

  def _FetchOsxFlags(self) -> int:
    """Fetches macOS extended file flags."""
    if platform.system() != "Darwin":
      return 0

    return self._stat.st_flags  # pytype: disable=attribute-error


class StatCache:
  """An utility class for avoiding unnecessary syscalls to `[l]stat`.

  This class is useful in situations where manual bookkeeping of stat results
  in order to prevent extra system calls becomes tedious and complicates control
  flow. This class makes sure that no unnecessary system calls are made and is
  smart enough to cache symlink results when a file is not a symlink.
  """

  _Key = NamedTuple("_Key", (("path", str), ("follow_symlink", bool)))  # pylint: disable=invalid-name

  def __init__(self):
    self._cache: dict[StatCache._Key, Stat] = {}

  def Get(self, path: str, follow_symlink: bool = True) -> Stat:
    """Stats given file or returns a cached result if available.

    Args:
      path: A path to the file to perform `stat` on.
      follow_symlink: True if `stat` of a file that a symlink points to should
        be returned instead of the symlink itself. For non-symlinks this setting
        has no effect.

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


def _NanosecondsToMicroseconds(ns: int) -> int:
  """Converts nanoseconds to microseconds."""
  return ns // 1000


def _SecondsToMicroseconds(ns: float) -> int:
  """Converts seconds to microseconds."""
  return int(ns * 1e6)
