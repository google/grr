#!/usr/bin/env python
# Lint as: python3
"""A module with utilities for a very simple chunked serialization format."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import os
import struct
from typing import IO
from typing import Iterator
from typing import Optional


def Write(buf: IO[bytes], chunk: bytes) -> None:
  """Writes a single chunk to the output buffer.

  Args:
    buf: An output buffer to write the chunk into.
    chunk: A chunk to write to the buffer.
  """
  buf.write(_UINT64.pack(len(chunk)))
  buf.write(chunk)


def Read(buf: IO[bytes]) -> Optional[bytes]:
  """Reads a single chunk from the input buffer.

  Args:
    buf: An input buffer to read the chunk from.

  Returns:
    A single chunk if it is available, `None` if the buffer is empty.

  Raises:
    ValueError: If the buffer contains incorrect sequence of bytes.
  """
  count_bytes = buf.read(_UINT64.size)
  if not count_bytes:
    return None

  try:
    (count,) = _UINT64.unpack(count_bytes)
  except struct.error as error:
    raise ValueError(f"Incorrect size tag {count_bytes}: {error}")

  # It might happen that we are given file with incorrect format. If the size
  # tag is interpreted as a huge number, reading the buffer will lead to raising
  # an exception, because Python will try to allocate a buffer to read into. If
  # possible, we try to check guard against such situations and provide more
  # informative exception message.

  def Error(left: int) -> ValueError:
    message = f"Malformed input (reading {count} bytes out of {left} available)"
    return ValueError(message)

  if buf.seekable():
    position = buf.tell()

    buf.seek(0, os.SEEK_END)
    size = buf.tell()

    if count > size - position:
      raise Error(size - position)

    buf.seek(position, os.SEEK_SET)

  chunk = buf.read(count)
  if len(chunk) != count:
    raise Error(len(chunk))

  return chunk


def ReadAll(buf: IO[bytes]) -> Iterator[bytes]:
  """Reads all the chunks from the input buffer (until the end).

  Args:
    buf: An input buffer to read the chunks from.

  Yields:
    Chunks of bytes stored in the buffer.

  Raises:
    ValueError: If the buffer contains an incorrect sequence of bytes.
  """
  while True:
    chunk = Read(buf)
    if chunk is None:
      return

    yield chunk


def Encode(chunk: bytes) -> bytes:
  """Encodes a single chunk to a blob of bytes in the chunked format.

  Args:
    chunk: A chunk to encode.

  Returns:
    A blob of bytes in the chunked format.
  """
  return _UINT64.pack(len(chunk)) + chunk


_UINT64 = struct.Struct("!Q")  # Network-endian 64-bit unsigned integer format.
