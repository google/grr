#!/usr/bin/env python
"""A module with utilities for working with the Sleuthkit's body format."""

from collections.abc import Iterator
import enum
import io
import stat
from typing import Optional

from grr_response_proto import timeline_pb2

DEFAULT_CHUNK_SIZE = 1024 * 1024  # 1 MiB.


# TODO(hanuszczak): Migrate this to dataclasses once we are Python 3.7+ only.
class Opts:
  """Options for generating files in the body format.

  Attributes:
    chunk_size: An (optional) size of the output chunk. Note that chunks are
      going to be slightly bigger than this value, but the difference should be
      negligible.
    timestamp_subsecond_precision: An (optional) flag that controls whether the
      output should use floating-point subsecond-precision timestamps.
    inode_ntfs_file_reference_format: An (optional) flag that controls whether
      the output should use NTFS file reference format for inode values.
    backslash_escape: An (optional) flag that controls whether the output should
      have backslashes escaped.
    carriage_return_escape: An (optional) flag that controls whether the output
      should escape carriage return character.
    non_printable_escape: An (optional) flag that controls whether non-printable
      ASCII characters should be escaped.
  """

  @enum.unique
  class InodeFormat(enum.Enum):
    """An enum class describing formatting of inode values."""

    # Raw integer value.
    RAW_INT = enum.auto()

    # NTFS file reference format [1].
    #
    # The NTFS file reference is a pair of the file record number in the MFT and
    # its sequence number. A textual representation of it is a dash-delimited
    # string of these two values (e.g. `1337-42`).
    #
    # [1]: https://flatcap.org/linux-ntfs/ntfs/concepts/file_reference.html
    NTFS_FILE_REFERENCE = enum.auto()

  chunk_size: int = DEFAULT_CHUNK_SIZE
  timestamp_subsecond_precision: bool = False
  inode_format: InodeFormat = InodeFormat.RAW_INT
  backslash_escape: bool = False
  carriage_return_escape: bool = False
  non_printable_escape: bool = False


def Stream(
    entries: Iterator[timeline_pb2.TimelineEntry],
    opts: Optional[Opts] = None,
) -> Iterator[bytes]:
  """Streams chunks of a Sleuthkit's body file (from a stream of entries).

  Args:
    entries: A stream of timeline entries protoes.
    opts: Options for the format of the generated file.

  Yields:
    Chunks of the body file.
  """
  if opts is None:
    opts = Opts()

  if opts.timestamp_subsecond_precision:
    timestamp_fmt = lambda ns: str(ns / 10**9)
  else:
    timestamp_fmt = lambda ns: str(ns // 10**9)

  inode_fmt = {
      Opts.InodeFormat.RAW_INT: str,
      Opts.InodeFormat.NTFS_FILE_REFERENCE: _NtfsFileReference,
  }[opts.inode_format]

  body_path_escape_table = dict(_BODY_PATH_ESCAPE_BASE_TABLE)
  if opts.carriage_return_escape:
    body_path_escape_table["\r"] = "\\r"
  if opts.backslash_escape:
    body_path_escape_table["\\"] = "\\\\"
  if opts.non_printable_escape:
    for char in _NON_PRINTABLE_ASCII:
      body_path_escape_table[char] = f"\\x{ord(char):02x}"

  path_trans = str.maketrans(body_path_escape_table)

  buf = io.StringIO()

  for entry in entries:
    path = entry.path.decode("utf-8", "surrogateescape")
    mode = entry.mode

    if not mode and entry.attributes:
      # If there is no mode but we have file attributes, we are most likely on
      # Windows so we just emulate mode similarly to what Python does [1].
      #
      # pylint: disable=line-too-long
      # [1]: https://github.com/python/cpython/blob/v3.13.7/Python/fileutils.c#L1077-L1090
      # pylint: enable=line-too-long
      if entry.attributes & _FILE_ATTRIBUTE_DIRECTORY:
        mode |= stat.S_IFDIR
      else:
        mode |= stat.S_IFREG
      if entry.attributes & _FILE_ATTRIBUTE_READONLY:
        mode |= 0o555
      else:
        mode |= 0o777

    # We don't generally want to use the built-in Python's CSV module for body
    # files because it very weirdly handles certain cases. For example, in non-
    # quote mode it will escape `\n` as `\\\n` (that is: a backslash followed by
    # a newline rather than a backslash followed by a normal `n` character).
    buf.write(str(0))
    buf.write("|")
    buf.write(path.translate(path_trans))
    buf.write("|")
    buf.write(inode_fmt(entry.ino))
    buf.write("|")
    buf.write(stat.filemode(mode))
    buf.write("|")
    buf.write(str(entry.uid))
    buf.write("|")
    buf.write(str(entry.gid))
    buf.write("|")
    buf.write(str(entry.size))
    buf.write("|")
    buf.write(timestamp_fmt(entry.atime_ns))
    buf.write("|")
    buf.write(timestamp_fmt(entry.mtime_ns))
    buf.write("|")
    buf.write(timestamp_fmt(entry.ctime_ns))
    buf.write("|")
    buf.write(timestamp_fmt(entry.btime_ns))
    buf.write("\n")

    if buf.tell() > opts.chunk_size:
      yield buf.getvalue().encode("utf-8", "surrogateescape")
      buf.truncate(0)
      buf.seek(0, io.SEEK_SET)

  leftover = buf.getvalue()
  if leftover:
    yield leftover.encode("utf-8", "surrogateescape")


# A path can have arbitrary bytes inside, so we do not attempt to escape every
# non-standard character. Rather, we only consider two that need to be handled:
# the newline character (since they denote rows) and pipes (since they denote
# columns). Everything else is passed as is and we do not give any special
# meaning to any other character (e.g. quotes).
#
# Note that this means the escaping is "lossy": two paths, e.g. one that has
# a backslash followed by an `n` character and a one that has a literal newline
# character inside are going to be represented the same way. This is not a big
# problem because the format is extremely underspecified anyway and is supposed
# to let the analyst quickly navigate the timeline. For precise and detailed
# data other timeline export formats should be used.
_BODY_PATH_ESCAPE_BASE_TABLE = {
    "\n": "\\n",
    "|": "\\|",
}

# Non-printable (control) characters are characters corresponding to code points
# from 0 to 31 or equal to 127 (the delete character). See [1] for more details.
#
# Note that Python's standard library offers `string.printable` set that could
# simplify this code. However, we don't use it since it makes some questionable
# decisions what is considered "printable" (e.g. vertical tabs or form feeds are
# included there).
#
# [1]: https://en.wikipedia.org/wiki/ASCII#Character_groups
_NON_PRINTABLE_ASCII = set(map(chr, range(32))) | {chr(0x7F)}


def _NtfsFileReference(ino: int) -> str:
  """Returns an NTFS file reference representation of the inode value."""
  # https://flatcap.org/linux-ntfs/ntfs/concepts/file_reference.html
  record = ino & ((1 << 48) - 1)
  sequence = ino >> 48
  return f"{record}-{sequence}"


# https://learn.microsoft.com/en-us/windows/win32/fileio/file-attribute-constants
_FILE_ATTRIBUTE_READONLY = 0x00000001
_FILE_ATTRIBUTE_DIRECTORY = 0x00000010
