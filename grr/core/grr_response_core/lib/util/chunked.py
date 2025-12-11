#!/usr/bin/env python
"""A module with utilities for a very simple chunked serialization format."""

from collections.abc import Iterator
import struct
from typing import IO, Optional


class Error(Exception):
  """Base error class for chunked module."""


class IncorrectSizeTagError(Error):
  """Raised when chunk size header can't be parsed."""


class ChunkSizeTooBigError(Error):
  """Raised when chunk header has what appears to be an invalid size."""


class ChunkTruncatedError(Error):
  """Raised when chunk appears to be truncated."""


def Write(buf: IO[bytes], chunk: bytes) -> None:
  """Writes a single chunk to the output buffer.

  Args:
    buf: An output buffer to write the chunk into.
    chunk: A chunk to write to the buffer.
  """
  buf.write(_UINT64.pack(len(chunk)))
  buf.write(chunk)


def Read(
    buf: IO[bytes], max_chunk_size: Optional[int] = None
) -> Optional[bytes]:
  """Reads a single chunk from the input buffer.

  Args:
    buf: An input buffer to read the chunk from.
    max_chunk_size: If set, will raise if chunk's size is larger than a given
      value.

  Returns:
    A single chunk if it is available, `None` if the buffer is empty.

  Raises:
    InvalidSizeTagError: if the buffer contains incorrect sequence of bytes.
    ChunkSizeTooBigError: if the read chunk size is larger than max_chunk_size.
    ChunkTruncatedError: if the read chunk size is smaller than what was
        manifested in the header.
  """
  count_bytes = buf.read(_UINT64.size)
  if not count_bytes:
    return None

  try:
    (count,) = _UINT64.unpack(count_bytes)
  except struct.error as error:
    raise IncorrectSizeTagError(f"Incorrect size tag {count_bytes}: {error}")

  # It might happen that we are given file with incorrect format. If the size
  # tag is interpreted as a huge number, reading the buffer will lead to raising
  # an exception, because Python will try to allocate a buffer to read into. If
  # possible, we try to check guard against such situations and provide more
  # informative exception message.

  if max_chunk_size is not None and count > max_chunk_size:
    raise ChunkSizeTooBigError(
        f"Malformed input: chunk size {count} is bigger than {max_chunk_size}"
    )

  chunk = buf.read(count)
  if len(chunk) != count:
    raise ChunkTruncatedError(
        f"Malformed input: chunk size {count} "
        f"is bigger than actual number of bytes read {len(chunk)}"
    )

  return chunk


def ReadAll(
    buf: IO[bytes],
) -> Iterator[bytes]:
  """Reads all the chunks from the input buffer (until the end).

  Args:
    buf: An input buffer to read the chunks from.

  Yields:
    Chunks of bytes stored in the buffer.

  Raises:
    InvalidSizeTagError if the buffer contains incorrect sequence of bytes.
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
