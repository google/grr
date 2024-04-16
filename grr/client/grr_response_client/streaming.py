#!/usr/bin/env python
"""Utility classes for streaming files and memory."""

import abc
import os
from typing import Iterator  # pylint: disable=unused-import
from typing import Optional


class Streamer(object):
  """An utility class for buffered processing.

  Input is divided into chunk objects that can be processed individually. If
  needed chunks returned by the streamer can overlap: suffix of one chunk will
  become prefix of the next one.

  Attributes:
    chunk_size: A number of bytes per chunk returned by the streamer object.
    overlap_size: A number of bytes that the next chunk will share with the
      previous one.
  """

  def __init__(self, chunk_size=None, overlap_size=0):
    if chunk_size is None:
      raise ValueError("chunk size must be specified")
    if overlap_size >= chunk_size:
      raise ValueError("chunk size must be strictly greater than overlap size")

    self.chunk_size = chunk_size
    self.overlap_size = overlap_size

  def StreamFile(self, filedesc, offset=0, amount=None):
    """Streams chunks of a given file starting at given offset.

    Args:
      filedesc: A `file` object to stream.
      offset: An integer offset at which the file stream should start on.
      amount: An upper bound on number of bytes to read.

    Returns:
      Generator over `Chunk` instances.
    """
    reader = FileReader(filedesc, offset=offset)
    return self.Stream(reader, amount=amount)

  def StreamFilePath(self, filepath, offset=0, amount=None):
    """Streams chunks of a file located at given path starting at given offset.

    Args:
      filepath: A path to the file to stream.
      offset: An integer offset at which the file stream should start on.
      amount: An upper bound on number of bytes to read.

    Yields:
      `Chunk` instances.
    """
    with open(filepath, "rb") as filedesc:
      for chunk in self.StreamFile(filedesc, offset=offset, amount=amount):
        yield chunk

  def StreamMemory(self, process, offset=0, amount=None):
    """Streams chunks of memory of a given process starting at given offset.

    Args:
      process: A platform-specific `Process` instance.
      offset: An integer offset at which the memory stream should start on.
      amount: An upper bound on number of bytes to read.

    Returns:
      Generator over `Chunk` instances.
    """
    reader = MemoryReader(process, offset=offset)
    return self.Stream(reader, amount=amount)

  def Stream(self, reader: "Reader", amount=None):
    """Streams chunks of a given file starting at given offset.

    Args:
      reader: A `Reader` instance.
      amount: An upper bound on number of bytes to read.

    Yields:
      `Chunk` instances.
    """
    if amount is None:
      amount = float("inf")

    data = reader.Read(min(self.chunk_size, amount))
    if not data:
      return

    amount -= len(data)
    offset = reader.offset - len(data)
    yield Chunk(offset=offset, data=data)

    while amount > 0:
      # We need `len(data)` here because overlap size can be 0.
      overlap = data[len(data) - self.overlap_size :]

      new = reader.Read(min(self.chunk_size - self.overlap_size, amount))
      if not new:
        return

      data = overlap + new

      amount -= len(new)
      offset = reader.offset - len(data)
      yield Chunk(offset=offset, data=data, overlap=len(overlap))

  def StreamRanges(self, offset: int, amount: int) -> "Iterator[Chunk]":
    """Breaks the interval `[offset, offset+amount)` into chunks.

    The chunks have no `data` set, only `offset` and `amount`.

    Args:
      offset: Offset to start at.
      amount: Size of the interval.

    Yields:
      `Chunk` instances.
    """
    if amount == 0:
      return

    yield Chunk(offset=offset, amount=min(self.chunk_size, amount))

    end = offset + amount
    pos = offset + self.chunk_size
    pos = min(pos, end)

    while pos < end:
      chunk_start = pos - self.overlap_size
      chunk_start = max(chunk_start, offset)

      chunk_end = chunk_start + self.chunk_size
      chunk_end = min(chunk_end, end)

      yield Chunk(
          offset=chunk_start,
          amount=(chunk_end - chunk_start),
          overlap=(pos - chunk_start),
          data=None,
      )
      pos = chunk_end


class Chunk(object):
  """A class representing part of a file.

  Args:
    offset: An offset at which this chunk occurs in its source file.
    data: An array of raw bytes this chunk represents.
    overlap: A number of bytes this chunk shares with the previous one.
  """

  def __init__(
      self,
      offset: Optional[int] = None,
      data: Optional[bytes] = None,
      overlap: int = 0,
      amount: Optional[int] = None,
  ):
    if offset is None:
      raise ValueError("chunk offset must be specified")
    if data is None and amount is None:
      raise ValueError("chunk data or amount must be specified")

    self.offset = offset
    self.data = data
    self.overlap = overlap
    if amount is None:
      self.amount = len(data)
    else:
      self.amount = amount

  def __repr__(self):
    return (
        f"Chunk<offset={self.offset}, amount={self.amount}, "
        f"overlap={self.overlap}>"
    )

  # TODO(hanuszczak): This function is beyond the scope of this module. It is
  # used in only one place [1] and should probably be moved there as well as
  # corresponding test.
  #
  # [1]: grr/client/client_actions/file_finder_utils/conditions.py
  def Scan(self, matcher):
    """Yields spans occurrences of a given pattern within the chunk.

    Only matches that span over regular (non-overlapped) chunk bytes are
    returned. Matches lying completely within the overlapped zone are ought to
    be returned by the previous chunk.

    Args:
      matcher: A `Matcher` instance corresponding to the searched pattern.

    Yields:
      `Matcher.Span` object corresponding to the positions of the pattern.
    """

    position = 0
    while True:
      span = matcher.Match(self.data, position)
      if span is None:
        return

      # We are not interested in hits within overlap-only zone. We continue the
      # search just after the previous match starts because of situations where
      # there is a match beginning before the end of the overlap-only zone match
      # and ending after the overlap zone.
      if span.end <= self.overlap:
        position = span.begin + 1
        continue

      # Since we do not care about overlapping matches we resume our search
      # at the end of the previous match.
      position = span.end
      yield span


class Reader(metaclass=abc.ABCMeta):
  """A unified interface for reader-like objects."""

  @abc.abstractproperty
  def offset(self):
    """An integer representing current position within the source."""

  @abc.abstractmethod
  def Read(self, amount):
    """An abstract method for reading byte segments.

    Args:
      amount: A number of bytes to read.

    Returns:
      Bytes that have been read.
    """


class FileReader(Reader):
  """A reader implementation that wraps ordinary file objects."""

  def __init__(self, filedesc, offset=0):
    """Initializes a new FileReader.

    Args:
      filedesc: A file descriptor object to read from.
      offset: An initial offset within the file.
    """
    super().__init__()

    self._filedesc = filedesc
    self._offset = offset
    filedesc.seek(offset, os.SEEK_SET)

  @property
  def offset(self):
    return self._offset

  def Read(self, amount):
    result = self._filedesc.read(amount)
    self._offset += len(result)
    return result


class MemoryReader(Reader):
  """A reader implementation that reads from process memory."""

  def __init__(self, process, offset=0):
    """Initializes a new MemoryReader.

    Args:
      process: A platform-specific `Process` instance.
      offset: An initial offset within the memory.
    """
    super().__init__()

    self._process = process
    self._offset = offset

  @property
  def offset(self):
    return self._offset

  def Read(self, amount):
    result = self._process.ReadBytes(self._offset, amount)
    self._offset += len(result)
    return result
