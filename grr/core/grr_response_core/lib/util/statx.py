#!/usr/bin/env python
"""A module for working with extended file stat collection.

This module will try to collect as detailed stat information as possible
depending on platform capabilities (e.g. on Linux it will use `statx` [1] call.

[1]: https://www.man7.org/linux/man-pages/man2/statx.2.html
"""
import ctypes
import functools
import operator
import os
import platform
from typing import NamedTuple


# Indicates whether the call also collects information about the birth time.
BTIME_SUPPORT: bool


# TODO(hanuszczak): Migrate to data classes on support for 3.7 is available.
class Result(NamedTuple):
  """A result of extended stat collection."""
  # A bitmask with extra file attributes.
  attributes: int
  # A number of hard links.
  nlink: int
  # A user identifier of the owner.
  uid: int
  # A group identifier of the owner.
  gid: int
  # A bitmask indicating the file and mode of the file.
  mode: int
  # An inode number of the file.
  ino: int
  # The total size (in bytes) of the file.
  size: int

  # Last access time (in nanoseconds since epoch).
  atime_ns: int
  # Last access time (in nanoseconds since epoch).
  btime_ns: int
  # Last access time (in nanoseconds since epoch).
  ctime_ns: int
  # Last access time (in nanoseconds since epoch).
  mtime_ns: int

  # The device identifier (if file represents a device).
  rdev: int
  # The device identifier of the filesystem the file resides on.
  dev: int


def Get(path: bytes) -> Result:
  """Collects detailed stat information about the path.

  Args:
    path: A path to the file for which the information should be retrieved.

  Returns:
    An object with detailed start information.
  """
  return _GetImpl(path)


class _StatxTimestampStruct(ctypes.Structure):
  """A low-level definition of Linux's stat timestamp type."""

  # https://elixir.bootlin.com/linux/v5.6/source/include/uapi/linux/stat.h
  _fields_ = [
      ("tv_sec", ctypes.c_int64),
      ("tv_nsec", ctypes.c_uint32),
      ("__reserved", ctypes.c_int32),
  ]

  @property
  def nanos(self):
    """A number of nanoseconds since epoch the timestamp represents."""
    return self.tv_sec * 10**9 + self.tv_nsec


class _StatxStruct(ctypes.Structure):
  """A low-level definition of Linux's stat object type."""

  # https://elixir.bootlin.com/linux/v5.6/source/include/uapi/linux/stat.h
  _fields_ = [
      ("stx_mask", ctypes.c_uint32),
      ("stx_blksize", ctypes.c_uint32),
      ("stx_attributes", ctypes.c_uint64),
      ("stx_nlink", ctypes.c_uint32),
      ("stx_uid", ctypes.c_uint32),
      ("stx_gid", ctypes.c_uint32),
      ("stx_mode", ctypes.c_uint16),
      ("__spare0", ctypes.c_uint16 * 1),
      ("stx_ino", ctypes.c_uint64),
      ("stx_size", ctypes.c_uint64),
      ("stx_blocks", ctypes.c_uint64),
      ("stx_attributes_mask", ctypes.c_uint64),
      # File timestamps.
      ("stx_atime", _StatxTimestampStruct),
      ("stx_btime", _StatxTimestampStruct),
      ("stx_ctime", _StatxTimestampStruct),
      ("stx_mtime", _StatxTimestampStruct),
      # Device identifier (if the file represents a device).
      ("stx_rdev_major", ctypes.c_uint32),
      ("stx_rdev_minor", ctypes.c_uint32),
      # Device identifier of the filesystem the file resides on.
      ("stx_dev_major", ctypes.c_uint32),
      ("stx_dev_minor", ctypes.c_uint32),
      # Spare space for future extensions.
      ("__spare2", ctypes.c_uint64 * 14),
  ]

  @property
  def rdev(self) -> int:
    """Device identifier (if the file represents a device)."""
    # https://elixir.bootlin.com/linux/v5.6/source/tools/include/nolibc/nolibc.h
    return ((self.stx_rdev_major & 0xfff) << 8) | (self.stx_rdev_minor & 0xff)

  @property
  def dev(self) -> int:
    """Device identifier of the filesystem the file resides on."""
    # https://elixir.bootlin.com/linux/v5.6/source/tools/include/nolibc/nolibc.h
    return ((self.stx_dev_major & 0xfff) << 8) | (self.stx_dev_minor & 0xff)


# https://elixir.bootlin.com/linux/v3.4/source/include/linux/fcntl.h
_AT_SYMLINK_NOFOLLOW = 0x100
_AT_STATX_SYNC_AS_STAT = 0x0000

# https://elixir.bootlin.com/linux/v5.8/source/include/uapi/linux/stat.h
_STATX_MODE = 0x00000002
_STATX_NLINK = 0x00000004
_STATX_UID = 0x00000008
_STATX_GID = 0x00000010
_STATX_ATIME = 0x00000020
_STATX_BTIME = 0x00000800
_STATX_MTIME = 0x00000040
_STATX_CTIME = 0x00000080
_STATX_INO = 0x00000100
_STATX_SIZE = 0x00000200
_STATX_ALL = functools.reduce(operator.__or__, [
    _STATX_MODE,
    _STATX_NLINK,
    _STATX_UID,
    _STATX_GID,
    _STATX_ATIME,
    _STATX_BTIME,
    _STATX_MTIME,
    _STATX_CTIME,
    _STATX_INO,
    _STATX_SIZE,
], 0)

if platform.system() == "Linux":

  _libc = ctypes.CDLL("libc.so.6")

  try:
    _statx = _libc.statx
  except AttributeError:
    # `statx` is available only since glibc 2.28.
    _statx = None

  if _statx is not None:

    _statx.argtypes = [
        # Input arguments.
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_uint,
        # Output arguments.
        ctypes.POINTER(_StatxStruct),
    ]
    _statx.restype = ctypes.c_int

    def _GetImplLinuxStatx(path: bytes) -> Result:
      """A Linux-specific stat implementation through `statx`."""
      c_result = _StatxStruct()
      c_status = _statx(0, path, _AT_SYMLINK_NOFOLLOW | _AT_STATX_SYNC_AS_STAT,
                        _STATX_ALL, ctypes.pointer(c_result))

      if c_status != 0:
        raise OSError(f"Failed to stat '{path}', error code: {c_status}")

      return Result(
          attributes=c_result.stx_attributes,
          nlink=c_result.stx_nlink,
          uid=c_result.stx_uid,
          gid=c_result.stx_gid,
          mode=c_result.stx_mode,
          ino=c_result.stx_ino,
          size=c_result.stx_size,
          atime_ns=c_result.stx_atime.nanos,
          btime_ns=c_result.stx_btime.nanos,
          ctime_ns=c_result.stx_ctime.nanos,
          mtime_ns=c_result.stx_mtime.nanos,
          rdev=c_result.rdev,
          dev=c_result.dev)

    _GetImpl = _GetImplLinuxStatx
    BTIME_SUPPORT = True

  else:

    def _GetImplLinux(path: bytes) -> Result:
      """A generic Linux-specific stat implementation."""
      stat_obj = os.lstat(path)
      return Result(
          attributes=0,  # Not available.
          nlink=stat_obj.st_nlink,
          uid=stat_obj.st_uid,
          gid=stat_obj.st_gid,
          mode=stat_obj.st_mode,
          ino=stat_obj.st_ino,
          size=stat_obj.st_size,
          atime_ns=stat_obj.st_atime_ns,
          btime_ns=0,  # Not available.
          ctime_ns=stat_obj.st_ctime_ns,
          mtime_ns=stat_obj.st_mtime_ns,
          rdev=stat_obj.st_rdev,
          dev=stat_obj.st_dev)

    _GetImpl = _GetImplLinux
    BTIME_SUPPORT = False

elif platform.system() == "Darwin":

  def _GetImplMacos(path: bytes) -> Result:
    """A macOS-specific stat implementation."""
    stat_obj = os.lstat(path)
    # Nanosecond-precision birthtime is not available, with approximate it with
    # the float-precision one.
    st_birthtime_ns = int(stat_obj.st_birthtime * 10**9)

    return Result(
        attributes=stat_obj.st_flags,
        nlink=stat_obj.st_nlink,
        uid=stat_obj.st_uid,
        gid=stat_obj.st_gid,
        mode=stat_obj.st_mode,
        ino=stat_obj.st_ino,
        size=stat_obj.st_size,
        atime_ns=stat_obj.st_atime_ns,
        btime_ns=st_birthtime_ns,
        ctime_ns=stat_obj.st_ctime_ns,
        mtime_ns=stat_obj.st_mtime_ns,
        rdev=stat_obj.st_rdev,
        dev=stat_obj.st_dev)

  _GetImpl = _GetImplMacos
  BTIME_SUPPORT = True

elif platform.system() == "Windows":

  def _GetImplWindows(path: bytes) -> Result:
    """A Windows-specific stat implementation."""
    stat_obj = os.lstat(path)

    # pylint: disable=line-too-long
    # On Windows, the `st_ctime` field is the file birth time [1], so we just
    # copy this value both to `btime` and `ctime`.
    #
    # [1]: https://docs.microsoft.com/en-us/cpp/c-runtime-library/reference/stat-functions
    # pylint: enable=line-too-long

    return Result(
        attributes=stat_obj.st_file_attributes,  # pytype: disable=attribute-error
        nlink=stat_obj.st_nlink,
        uid=stat_obj.st_uid,
        gid=stat_obj.st_gid,
        mode=stat_obj.st_mode,
        ino=stat_obj.st_ino,
        size=stat_obj.st_size,
        atime_ns=stat_obj.st_atime_ns,
        btime_ns=stat_obj.st_ctime_ns,
        ctime_ns=stat_obj.st_ctime_ns,
        mtime_ns=stat_obj.st_mtime_ns,
        rdev=0,  # Not available.
        dev=stat_obj.st_dev)

  _GetImpl = _GetImplWindows
  BTIME_SUPPORT = True
