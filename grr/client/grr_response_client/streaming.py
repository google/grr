#!/usr/bin/env python
"""Utility classes for streaming files and memory."""


class FileStreamer(object):
  """An utility class for buffered file processing.

  File is divided into chunk objects that can be processed individually. If
  needed chunks returned by the streamer can overlap: suffix of one chunk will
  become prefix of a next one.

  Args:
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

  def StreamFile(self, fd, offset=0, amount=None):
    """Yields chunks of a given file starting at given offset.

    Args:
      fd: A file descriptor for a file to stream.
      offset: An integer offset at which the file stream should start on.
      amount: An upper bound on number of bytes to read.

    Raises:
      ValueError: If the amount of bytes is not specified.
    """
    if amount is None:
      raise ValueError("the amount of bytes to read must be specified")

    fd.seek(offset)

    data = fd.read(min(self.chunk_size, amount))
    if not data:
      return

    yield Chunk(offset=offset, data=data)

    amount -= len(data)
    offset += len(data) - self.overlap_size

    while amount > 0:
      # We need `len(data)` here because overlap size can be 0.
      overlap = data[len(data) - self.overlap_size:]
      new = fd.read(min(self.chunk_size - self.overlap_size, amount))
      if not new:
        return

      data = overlap + new
      yield Chunk(offset=offset, data=data, overlap=len(overlap))

      amount -= len(new)
      offset += len(new)

  def StreamFilePath(self, path, offset=0, amount=None):
    """Yields chunks of a file located at given path starting at given offset.

    Args:
      path: A path to the file to stream.
      offset: An integer offset at which the file stream should start on.
      amount: An upper bound on number of bytes to read.
    """
    with open(path, "rb") as fd:
      for chunk in self.StreamFile(fd, offset, amount):
        yield chunk


class MemoryStreamer(object):
  """Utility class to stream process memory in chunks."""

  def __init__(self, process, chunk_size=None, overlap_size=0):
    if process is None:
      raise ValueError("process must be specified")
    if chunk_size is None:
      raise ValueError("chunk size must be specified")
    if overlap_size >= chunk_size:
      raise ValueError("chunk size must be strictly greater thank overlap size")

    self.chunk_size = chunk_size
    self.overlap_size = overlap_size
    self.process = process

  def Stream(self, offset=0, amount=None):
    """Yields chunks of a given file starting at given offset.

    Args:
      offset: An integer offset at which the file stream should start on.
      amount: An upper bound on number of bytes to read.

    Raises:
      ValueError: If the amount of bytes is not specified.
    """
    if amount is None:
      raise ValueError("the amount of bytes to read must be specified")

    data = self.process.ReadBytes(offset, min(self.chunk_size, amount))
    if not data:
      return

    yield Chunk(offset=offset, data=data)

    amount -= len(data)
    offset += len(data) - self.overlap_size

    while amount > 0:
      # We need `len(data)` here because overlap size can be 0.
      overlap = data[len(data) - self.overlap_size:]
      new = self.process.ReadBytes(offset + self.overlap_size,
                                   min(self.chunk_size - self.overlap_size,
                                       amount))
      if not new:
        return

      data = overlap + new
      yield Chunk(offset=offset, data=data, overlap=len(overlap))

      amount -= len(new)
      offset += len(new)


class Chunk(object):
  """A class representing part of a file.

  Args:
    offset: An offset at which this chunk occurs in its source file.
    data: An array of raw bytes this chunk represents.
    overlap: A number of bytes this chunk shares with the previous one.
  """

  def __init__(self, offset=None, data=None, overlap=0):
    if offset is None:
      raise ValueError("chunk offset must be specified")
    if data is None:
      raise ValueError("chunk data must be specified")

    self.offset = offset
    self.data = data
    self.overlap = overlap

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
