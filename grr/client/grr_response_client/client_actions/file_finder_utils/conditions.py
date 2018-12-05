#!/usr/bin/env python
"""Implementation of condition mechanism for client-side file-finder."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import abc
import collections


from future.utils import with_metaclass

from grr_response_client import streaming
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder


class MetadataCondition(with_metaclass(abc.ABCMeta, object)):
  """An abstract class representing conditions on the file metadata."""

  @abc.abstractmethod
  def Check(self, stat):
    """Checks whether condition is met.

    Args:
      stat: An `utils.Stat` object.

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
    super(ModificationTimeCondition, self).__init__()
    self.params = params.modification_time

  def Check(self, stat):
    min_mtime = self.params.min_last_modified_time.AsSecondsSinceEpoch()
    max_mtime = self.params.max_last_modified_time.AsSecondsSinceEpoch()
    return min_mtime <= stat.GetModificationTime() <= max_mtime


class AccessTimeCondition(MetadataCondition):
  """A condition checking access time of a file."""

  def __init__(self, params):
    super(AccessTimeCondition, self).__init__()
    self.params = params.access_time

  def Check(self, stat):
    min_atime = self.params.min_last_access_time.AsSecondsSinceEpoch()
    max_atime = self.params.max_last_access_time.AsSecondsSinceEpoch()
    return min_atime <= stat.GetAccessTime() <= max_atime


class InodeChangeTimeCondition(MetadataCondition):
  """A condition checking change time of inode of a file."""

  def __init__(self, params):
    super(InodeChangeTimeCondition, self).__init__()
    self.params = params.inode_change_time

  def Check(self, stat):
    min_ctime = self.params.min_last_inode_change_time.AsSecondsSinceEpoch()
    max_ctime = self.params.max_last_inode_change_time.AsSecondsSinceEpoch()
    return min_ctime <= stat.GetChangeTime() <= max_ctime


class SizeCondition(MetadataCondition):
  """A condition checking size of a file."""

  def __init__(self, params):
    super(SizeCondition, self).__init__()
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
    super(ExtFlagsCondition, self).__init__()
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


class ContentCondition(with_metaclass(abc.ABCMeta, object)):
  """An abstract class representing conditions on the file contents."""

  @abc.abstractmethod
  def Search(self, path):
    """Searches specified file for particular content.

    Args:
      path: A path to the file that is going to be searched.

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

  def Scan(self, path, matcher):
    """Scans given file searching for occurrences of given pattern.

    Args:
      path: A path to the file that needs to be searched.
      matcher: A matcher object specifying a pattern to search for.

    Yields:
      `BufferReference` objects pointing to file parts with matching content.
    """
    streamer = streaming.Streamer(
        chunk_size=self.CHUNK_SIZE, overlap_size=self.OVERLAP_SIZE)

    offset = self.params.start_offset
    amount = self.params.length
    for chunk in streamer.StreamFilePath(path, offset=offset, amount=amount):
      for span in chunk.Scan(matcher):
        ctx_begin = max(span.begin - self.params.bytes_before, 0)
        ctx_end = min(span.end + self.params.bytes_after, len(chunk.data))
        ctx_data = chunk.data[ctx_begin:ctx_end]

        yield rdf_client.BufferReference(
            offset=chunk.offset + ctx_begin,
            length=len(ctx_data),
            data=ctx_data)

        if self.params.mode == self.params.Mode.FIRST_HIT:
          return


class LiteralMatchCondition(ContentCondition):
  """A content condition that lookups a literal pattern."""

  def __init__(self, params):
    super(LiteralMatchCondition, self).__init__()
    self.params = params.contents_literal_match

  def Search(self, path):
    matcher = LiteralMatcher(utils.SmartStr(self.params.literal))
    for match in self.Scan(path, matcher):
      yield match


class RegexMatchCondition(ContentCondition):
  """A content condition that lookups regular expressions."""

  def __init__(self, params):
    super(RegexMatchCondition, self).__init__()
    self.params = params.contents_regex_match

  def Search(self, path):
    matcher = RegexMatcher(self.params.regex)
    for match in self.Scan(path, matcher):
      yield match


class Matcher(with_metaclass(abc.ABCMeta, object)):
  """An abstract class for objects able to lookup byte strings."""

  Span = collections.namedtuple("Span", ["begin", "end"])  # pylint: disable=invalid-name

  @abc.abstractmethod
  def Match(self, data, position):
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

  # TODO(hanuszczak): This class should operate on normal Python regexes, not on
  # RDF values.

  def __init__(self, regex):
    super(RegexMatcher, self).__init__()
    self.regex = regex

  def Match(self, data, position):
    match = self.regex.Search(data[position:])
    if not match:
      return None

    begin, end = match.span()
    return Matcher.Span(begin=position + begin, end=position + end)


class LiteralMatcher(Matcher):
  """An exact string matcher that conforms to the `Matcher` interface.

  Args:
    literal: A byte string pattern that the matcher matches.
  """

  def __init__(self, literal):
    super(LiteralMatcher, self).__init__()
    self.literal = literal

  def Match(self, data, position):
    offset = data.find(self.literal, position)
    if offset == -1:
      return None

    return Matcher.Span(begin=offset, end=offset + len(self.literal))
