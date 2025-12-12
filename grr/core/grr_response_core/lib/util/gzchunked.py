#!/usr/bin/env python
"""A module with utilities for a very simple serialization format."""

from collections.abc import Iterator
import gzip
import io
import os
import struct

from grr_response_core.lib.util import chunked

DEFAULT_CHUNK_SIZE = 1 * 1024 * 1024  # 1 MiB.


def Serialize(
    stream: Iterator[bytes],
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> Iterator[bytes]:
  """Serializes a stream of data to the stream of chunks.

  Args:
    stream: A stream of data to serialize.
    chunk_size: An (optional) approximate size of a chunk in bytes. Every non-
      final chunk will be slightly bigger than the specified number, but this
      should be negligible.

  Yields:
    Serialized chunks (in the gzchunked format).
  """
  while True:
    buf = io.BytesIO()
    buf_entry_count = 0

    with gzip.GzipFile(fileobj=buf, mode="wb") as filedesc:
      for data in stream:
        chunked.Write(filedesc, data)  # pytype: disable=wrong-arg-types
        buf_entry_count += 1

        if buf.tell() >= chunk_size:
          break

    if buf_entry_count == 0:
      break

    yield buf.getvalue()


def Deserialize(stream: Iterator[bytes]) -> Iterator[bytes]:
  """Deserializes a stream a chunks into a stream of data.

  Args:
    stream: A stream of serialized chunks (in the gzchunked format).

  Yields:
    A stream of deserialized data.
  """
  for chunk in stream:
    buf = io.BytesIO(chunk)

    with gzip.GzipFile(fileobj=buf, mode="rb") as filedesc:
      filedesc.seek(0, os.SEEK_END)
      fd_size = filedesc.tell()
      filedesc.seek(0, os.SEEK_SET)

      while True:
        data = chunked.Read(filedesc, max_chunk_size=fd_size)  # pytype: disable=wrong-arg-types
        if data is None:
          break

        fd_size -= len(data)
        yield data


_UINT64 = struct.Struct("!Q")  # Network-endian 64-bit unsigned integer format.
