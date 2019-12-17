#!/usr/bin/env python
"""A module with utilities for a very simple serialization format."""
from __future__ import absolute_import
from __future__ import division

from __future__ import unicode_literals

import gzip
import io
import struct

from typing import Iterator

DEFAULT_CHUNK_SIZE = 4 * 1024 * 1024  # 4 MiB.


def Serialize(
    stream,
    chunk_size = DEFAULT_CHUNK_SIZE,
):
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
        filedesc.write(_UINT64.pack(len(data)))
        filedesc.write(data)
        buf_entry_count += 1

        if len(buf.getvalue()) >= chunk_size:
          break

    if buf_entry_count == 0:
      break

    yield buf.getvalue()


def Deserialize(stream):
  """Deserializes a stream a chunks into a stream of data.

  Args:
    stream: A stream of serialized chunks (in the gzchunked format).

  Yields:
    A stream of deserialized data.
  """
  for chunk in stream:
    buf = io.BytesIO(chunk)

    with gzip.GzipFile(fileobj=buf, mode="rb") as filedesc:
      while True:
        count = filedesc.read(_UINT64.size)
        if not count:
          break
        elif len(count) != _UINT64.size:
          raise ValueError("Incorrect gzchunked data size")

        (count,) = _UINT64.unpack(count)

        data = filedesc.read(count)
        if len(data) != count:
          raise ValueError("Content too short")

        yield data


_UINT64 = struct.Struct("!Q")  # Network-endian 64-bit unsigned integer format.
