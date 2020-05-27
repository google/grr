#!/usr/bin/env python
# Lint as: python3
"""A module with utilities for working with the Sleuthkit's body format."""

import stat

from typing import Iterator

from grr_response_proto import timeline_pb2

DEFAULT_CHUNK_SIZE = 1024 * 1024  # 1 MiB.

_CSV_TRANS = str.maketrans({'"': '""'})


def _CsvEscape(s: str) -> str:
  """Escapes a csv string per https://tools.ietf.org/html/rfc4180#page-2."""
  if "|" not in s and "\"" not in s and "\n" not in s and "\r" not in s:
    return s

  return f'"{s.translate(_CSV_TRANS)}"'


def Stream(
    entries: Iterator[timeline_pb2.TimelineEntry],
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> Iterator[bytes]:
  """Streams chunks of a Sleuthkit's body file (from a stream of entries).

  Args:
    entries: A stream of timeline entries protoes.
    chunk_size: An (optional) size of the output chunk. Note that chunks are
      going to be slightly bigger than this value, but the difference should be
      negligible.

  Yields:
    Chunks of the body file.
  """
  rows = []
  total_size = 0

  # Concatenating columns and rows via join seems to be ~15% faster than
  # using the csv.writer.
  for entry in entries:
    row = "|".join([
        "0",  # md5
        # Note that Sleuthkit's original FLS/mactime tools do not seem
        # to do any escaping/quoting:
        # https://github.com/sleuthkit/sleuthkit/blob/97a1e53f486bf05fd8e935298f72632706f26fa2/tsk/fs/fs_name.c#L635
        # https://github.com/sleuthkit/sleuthkit/blob/6dc7a922cbad958d1b2847c24f8d7e59fba97a84/tools/timeline/mactime.base#L941
        #
        # Using a custom CSV escaping function here, since it's much faster than
        # csv.writer: we know that we only have to escape a single column,
        # namely - the path column. All other columns are safe to write
        # as is.
        _CsvEscape(entry.path.decode("utf-8", "surrogateescape")),  # path
        str(entry.ino),  # ino
        stat.filemode(entry.mode),  # mode
        str(entry.uid),  # uid
        str(entry.gid),  # gid
        str(entry.size),  # size
        str(entry.atime_ns // 10**9),  # atime
        str(entry.mtime_ns // 10**9),  # mtime
        str(entry.ctime_ns // 10**9),  # ctime
        "0",  # crtime
    ]).encode("utf-8")

    # Account for the newline.
    total_size += len(row) + 1
    rows.append(row)

    if total_size > chunk_size:
      # Ensure the newline after the last row in this batch.
      rows.append(b"")
      yield b"\n".join(rows)

      total_size = 0
      rows = []

  if rows:
    # Ensure the newline after the last row.
    rows.append(b"")
    yield b"\n".join(rows)
