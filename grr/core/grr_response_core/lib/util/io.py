#!/usr/bin/env python
"""A module with utilities for working with I/O."""

from collections.abc import Iterator
import io
from typing import IO


def Chunk(stream: IO[bytes], size: int) -> Iterator[bytes]:
  """Divides given stream into chunks of specified size.

  Args:
    stream: A file-like object to chunk.
    size: Size of individual chunks (the last one might be smaller).

  Yields:
    Chunks with content of the stream.
  """
  if size <= 0:
    raise ValueError(f"Non-positive chunk size: {size}")

  while True:
    data = stream.read(size)
    if not data:
      break

    yield data


def Unchunk(chunks: Iterator[bytes]) -> IO[bytes]:
  """Joins chunks of a file to a file-like object.

  Args:
    chunks: An iterator yielding chunks of the file.

  Returns:
    A file-like object that
  """
  # For some reason the linter doesn't understand that `RawIOBase` implements
  # the `IO[bytes]` interface and complains.
  return io.BufferedReader(_Unchunked(chunks))  # pylint: disable=abstract-class-instantiated


class _Unchunked(io.RawIOBase, IO[bytes]):  # pytype: disable=signature-mismatch  # overriding-return-type-checks
  """A raw file-like object that reads chunk stream on demand."""

  def __init__(self, chunks: Iterator[bytes]) -> None:
    """Initializes the object."""
    super().__init__()
    self._chunks = chunks
    self._buf = io.BytesIO()

  def readable(self) -> bool:
    return True

  def readall(self) -> bytes:
    return b"".join(self._chunks)

  def readinto(self, buf: bytearray) -> int:
    if self._buf.tell() == len(self._buf.getbuffer()):
      self._buf.seek(0, io.SEEK_SET)
      self._buf.truncate()
      self._buf.write(next(self._chunks, b""))
      self._buf.seek(0, io.SEEK_SET)

    return self._buf.readinto(buf)
