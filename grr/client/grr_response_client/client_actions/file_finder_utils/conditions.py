#!/usr/bin/env python
"""Implementation of condition mechanism for client-side file-finder."""

import abc
import re
from typing import Iterator
from typing import NamedTuple
from typing import Optional
from typing import Pattern

from grr_response_client import streaming
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.util import precondition


class MetadataCondition(metaclass=abc.ABCMeta):
  """An abstract class representing conditions on the file metadata."""

  @abc.abstractmethod
  def Check(self, stat):
    """Checks whether condition is met.

    Args:
      stat: An `util.filesystem.Stat` object.

    Returns:
      True if the condition is met.
    """
    pass

  @staticmethod
  def Parse(conditions):
    """Parses the file finder condition types into the condition objects.

    Args:
      conditions: An iterator over `FileFinderCondition` objects.

    Yields:
      `MetadataCondition` objects that correspond to the file-finder conditions.
    """
    kind = rdf_file_finder.FileFinderCondition.Type
    classes = {
        kind.MODIFICATION_TIME: ModificationTimeCondition,
        kind.ACCESS_TIME: AccessTimeCondition,
        kind.INODE_CHANGE_TIME: InodeChangeTimeCondition,
        kind.SIZE: SizeCondition,
        kind.EXT_FLAGS: ExtFlagsCondition,
    }

    for condition in conditions:
      try:
        yield classes[condition.condition_type](condition)
      except KeyError:
        pass


class ModificationTimeCondition(MetadataCondition):
  """A condition checking modification time of a file."""

  def __init__(self, params):
    super().__init__()
    self.params = params.modification_time

  def Check(self, stat):
    min_mtime = self.params.min_last_modified_time.AsMicrosecondsSinceEpoch()
    max_mtime = self.params.max_last_modified_time.AsMicrosecondsSinceEpoch()
    return min_mtime <= stat.GetModificationTime() <= max_mtime


class AccessTimeCondition(MetadataCondition):
  """A condition checking access time of a file."""

  def __init__(self, params):
    super().__init__()
    self.params = params.access_time

  def Check(self, stat):
    min_atime = self.params.min_last_access_time.AsMicrosecondsSinceEpoch()
    max_atime = self.params.max_last_access_time.AsMicrosecondsSinceEpoch()
    return min_atime <= stat.GetAccessTime() <= max_atime


class InodeChangeTimeCondition(MetadataCondition):
  """A condition checking change time of inode of a file."""

  def __init__(self, params):
    super().__init__()
    self.params = params.inode_change_time

  def Check(self, stat):
    params = self.params

    min_ctime = params.min_last_inode_change_time.AsMicrosecondsSinceEpoch()
    max_ctime = params.max_last_inode_change_time.AsMicrosecondsSinceEpoch()
    return min_ctime <= stat.GetChangeTime() <= max_ctime


class SizeCondition(MetadataCondition):
  """A condition checking size of a file."""

  def __init__(self, params):
    super().__init__()
    self.params = params.size

  def Check(self, stat):
    min_fsize = self.params.min_file_size
    max_fsize = self.params.max_file_size
    return min_fsize <= stat.GetSize() <= max_fsize


class ExtFlagsCondition(MetadataCondition):
  """A condition checking extended flags of a file.

  Args:
    params: A `FileFinderCondition` instance.
  """

  def __init__(self, params):
    super().__init__()
    self.params = params.ext_flags

  def Check(self, stat):
    return self.CheckOsx(stat) and self.CheckLinux(stat)

  def CheckLinux(self, stat):
    flags = stat.GetLinuxFlags()
    bits_set = self.params.linux_bits_set
    bits_unset = self.params.linux_bits_unset
    return (bits_set & flags) == bits_set and (bits_unset & flags) == 0

  def CheckOsx(self, stat):
    flags = stat.GetOsxFlags()
    bits_set = self.params.osx_bits_set
    bits_unset = self.params.osx_bits_unset
    return (bits_set & flags) == bits_set and (bits_unset & flags) == 0


class ContentCondition(metaclass=abc.ABCMeta):
  """An abstract class representing conditions on the file contents."""

  @abc.abstractmethod
  def Search(self, fd):
    """Searches specified file for particular content.

    Args:
      fd: A file descriptor of the file that needs to be searched.

    Yields:
      `BufferReference` objects pointing to file parts with matching content.
    """
    pass

  @staticmethod
  def Parse(conditions):
    """Parses the file finder condition types into the condition objects.

    Args:
      conditions: An iterator over `FileFinderCondition` objects.

    Yields:
      `ContentCondition` objects that correspond to the file-finder conditions.
    """
    kind = rdf_file_finder.FileFinderCondition.Type
    classes = {
        kind.CONTENTS_LITERAL_MATCH: LiteralMatchCondition,
        kind.CONTENTS_REGEX_MATCH: RegexMatchCondition,
    }

    for condition in conditions:
      try:
        yield classes[condition.condition_type](condition)
      except KeyError:
        pass

  OVERLAP_SIZE = 1024 * 1024
  CHUNK_SIZE = 10 * 1024 * 1024

  def Scan(
      self,
      fd,
      matcher: "Matcher",
  ) -> Iterator[rdf_client.BufferReference]:
    """Scans given file searching for occurrences of given pattern.

    Args:
      fd: A file descriptor of the file that needs to be searched.
      matcher: A matcher object specifying a pattern to search for.

    Yields:
      `BufferReference` objects pointing to file parts with matching content.
    """
    streamer = streaming.Streamer(
        chunk_size=self.CHUNK_SIZE, overlap_size=self.OVERLAP_SIZE
    )

    offset = self.params.start_offset
    amount = self.params.length
    for chunk in streamer.StreamFile(fd, offset=offset, amount=amount):
      for span in chunk.Scan(matcher):
        ctx_begin = max(span.begin - self.params.bytes_before, 0)
        ctx_end = min(span.end + self.params.bytes_after, len(chunk.data))
        ctx_data = chunk.data[ctx_begin:ctx_end]

        yield rdf_client.BufferReference(
            offset=chunk.offset + ctx_begin, length=len(ctx_data), data=ctx_data
        )

        if self.params.mode == self.params.Mode.FIRST_HIT:
          return


class LiteralMatchCondition(ContentCondition):
  """A content condition that lookups a literal pattern."""

  def __init__(self, params):
    super().__init__()
    self.params = params.contents_literal_match

  def Search(self, fd):
    matcher = LiteralMatcher(self.params.literal.AsBytes())
    for match in self.Scan(fd, matcher):
      yield match


class RegexMatchCondition(ContentCondition):
  """A content condition that lookups regular expressions."""

  def __init__(self, params):
    super().__init__()
    self.params = params.contents_regex_match

  def Search(self, fd) -> Iterator[rdf_client.BufferReference]:
    regex = re.compile(self.params.regex.AsBytes(), flags=re.I | re.S | re.M)

    matcher = RegexMatcher(regex)
    for match in self.Scan(fd, matcher):
      yield match


class Matcher(metaclass=abc.ABCMeta):
  """An abstract class for objects able to lookup byte strings."""

  Span = NamedTuple("Span", [("begin", int), ("end", int)])  # pylint: disable=invalid-name

  @abc.abstractmethod
  def Match(self, data: bytes, position: int) -> Optional["Matcher.Span"]:
    """Matches the given data object starting at specified position.

    Args:
      data: A byte string to pattern match on.
      position: First position at which the search is started on.

    Returns:
      A `Span` object if the matcher finds something in the data.
    """
    pass


class RegexMatcher(Matcher):
  """A regex wrapper that conforms to the `Matcher` interface.

  Args:
    regex: An RDF regular expression that the matcher represents.
  """

  def __init__(self, regex: Pattern[bytes]):
    precondition.AssertType(regex, Pattern)

    super().__init__()
    self._regex = regex

  def Match(self, data: bytes, position: int) -> Optional[Matcher.Span]:
    precondition.AssertType(data, bytes)
    precondition.AssertType(position, int)

    match = self._regex.search(data[position:])
    if not match:
      return None

    begin, end = match.span()
    return Matcher.Span(begin=position + begin, end=position + end)


class LiteralMatcher(Matcher):
  """An exact string matcher that conforms to the `Matcher` interface.

  Args:
    literal: A byte string pattern that the matcher matches.
  """

  def __init__(self, literal: bytes):
    precondition.AssertType(literal, bytes)

    super().__init__()
    self._literal = literal

  def Match(self, data: bytes, position: int) -> Optional[Matcher.Span]:
    precondition.AssertType(data, bytes)
    precondition.AssertType(position, int)

    offset = data.find(self._literal, position)
    if offset == -1:
      return None

    return Matcher.Span(begin=offset, end=offset + len(self._literal))
