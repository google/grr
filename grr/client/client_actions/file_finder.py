#!/usr/bin/env python
"""The file finder client action."""

import abc
import collections
import errno
import fnmatch
import itertools
import logging
import os
import platform
import re

import psutil

from grr.client import actions
from grr.client import client_utils
from grr.client import client_utils_common
from grr.client import streaming
from grr.client.vfs_handlers import files

from grr.lib import utils
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import file_finder as rdf_file_finder
from grr.lib.rdfvalues import paths as rdf_paths


class Component(object):
  """A component of a path."""

  def __hash__(self):
    return hash(self.__str__())

  def Generate(self, base_path):
    raise NotImplementedError()


class RecursiveComponent(Component):
  """A recursive component."""

  def __init__(self, depth, follow_links=False, mountpoints_blacklist=None):
    self.depth = depth
    self.follow_links = follow_links
    self.mountpoints_blacklist = mountpoints_blacklist

  def Generate(self, base_path):
    for f in self._Generate(base_path, []):
      yield f

  def _Generate(self, base_path, relative_components):
    """Generates the relative filenames."""

    new_base = os.path.join(base_path, *relative_components)
    if not relative_components:
      yield new_base
    try:
      filenames = os.listdir(new_base)
    except OSError as e:
      if e.errno == errno.EACCES:  # permission denied.
        logging.info(e)
      return

    for f in filenames:
      new_components = relative_components + [f]
      relative_name = os.path.join(*new_components)
      yield relative_name

      if len(new_components) >= self.depth:
        continue

      filename = os.path.join(base_path, relative_name)
      try:
        stat = utils.Stat(filename)
        if not stat.IsDirectory():
          continue
        if filename in self.mountpoints_blacklist:
          continue
        if (not self.follow_links and
            utils.Stat(filename, follow_symlink=False).IsSymlink()):
          continue
        for res in self._Generate(base_path, new_components):
          yield res
      except OSError as e:
        if e.errno not in [errno.ENOENT, errno.ENOTDIR, errno.EINVAL]:
          logging.info(e)

  def __str__(self):
    return "%s:%s" % (self.__class__, self.depth)


class RegexComponent(Component):
  """A component matching the file name against a regex."""

  def __init__(self, regex):
    self.regex = re.compile(regex, flags=re.I)

  def Generate(self, base_path):
    try:
      for f in os.listdir(base_path):
        if self.regex.match(f):
          yield f
    except OSError as e:
      if e.errno == errno.EACCES:  # permission denied.
        logging.error(e)

  def __str__(self):
    return "%s:%s" % (self.__class__, self.regex)


class LiteralComponent(Component):
  """A component matching literal names."""

  def __init__(self, literal):
    self.literal = literal

  def Generate(self, base_path):
    corrected_matches = []
    literal_lower = self.literal.lower()

    try:
      for c in os.listdir(base_path):
        # Perfect match.
        if c == self.literal:
          yield self.literal
          return

        # Case correction.
        if c.lower() == literal_lower:
          corrected_matches.append(c)

      for m in corrected_matches:
        yield m

    except OSError as e:
      if e.errno == errno.EACCES:  # permission denied.
        logging.error(e)

  def __str__(self):
    return "%s:%s" % (self.__class__, self.literal)


class FileFinderOS(actions.ActionPlugin):
  """The file finder implementation using the OS file api."""

  in_rdfvalue = rdf_file_finder.FileFinderArgs
  out_rdfvalues = [rdf_file_finder.FileFinderResult]

  # This regex finds grouping patterns
  # (e.g. {test.exe,foo.doc,bar.txt}) and interpolations
  # (%%users.homedir%%).
  GROUPING_PATTERN = re.compile("({([^}]+,[^}]+)}|%%([^%]+?)%%)")

  # This regex finds recursions (C:\**, /usr/bin/**2).
  RECURSION_REGEX = re.compile(r"\*\*(\d*)")

  # A regex indicating if there are shell globs in this path.
  GLOB_MAGIC_CHECK = re.compile("[*?[]")

  def Run(self, args):
    self.follow_links = args.follow_links
    self.process_non_regular_files = args.process_non_regular_files

    # Generate a list of mount points where we stop recursive searches.
    if args.xdev == args.XDev.NEVER:
      # Never cross device boundaries, stop at all mount points.
      self.mountpoints_blacklist = set(
          [p.mountpoint for p in psutil.disk_partitions(all=True)])
    elif args.xdev == args.XDev.LOCAL:
      # Descend into file systems on physical devices only.
      self.mountpoints_blacklist = (
          set([p.mountpoint for p in psutil.disk_partitions(all=True)]) -
          set([p.mountpoint for p in psutil.disk_partitions(all=False)]))
    elif args.xdev == args.XDev.ALWAYS:
      # Never stop at any device boundary.
      self.mountpoints_blacklist = set()

    for fname in self.CollectGlobs(args.paths):
      self.Progress()
      self._ProcessFilePath(fname, args)

  def _ProcessFilePath(self, path, args):
    try:
      stat = utils.Stat(path, follow_symlink=False)
    except OSError:
      return

    if (not (stat.IsRegular() or stat.IsDirectory()) and
        not self.process_non_regular_files):
      return

    for metadata_condition in MetadataCondition.Parse(args.conditions):
      if not metadata_condition.Check(stat):
        return

    matches = []
    for content_condition in ContentCondition.Parse(args.conditions):
      result = list(content_condition.Search(path))
      if not result:
        return

      matches.extend(result)

    result = self._ProcessFile(path, stat, args)
    if result:
      result.matches = matches
      self.SendReply(result)

  def _ProcessFile(self, fname, stat, args):
    if args.action.action_type == args.action.Action.STAT:
      return self._ExecuteStat(fname, stat, args)

    # For directories, only Stat makes sense.
    if stat.IsDirectory():
      return None

    # We never want to hash/download the link, always the target.
    if stat.IsSymlink():
      try:
        stat = utils.Stat(fname, follow_symlink=True)
      except OSError:
        return None

    if args.action.action_type == args.action.Action.DOWNLOAD:
      return self._ExecuteDownload(fname, stat, args)

    if args.action.action_type == args.action.Action.HASH:
      return self._ExecuteHash(fname, stat, args)

    raise ValueError("incorrect action type: %s" % args.action.action_type)

  def _ExecuteStat(self, fname, stat, args):
    stat_entry = self.Stat(fname, stat, args.action.stat)
    return rdf_file_finder.FileFinderResult(stat_entry=stat_entry)

  def _ExecuteDownload(self, fname, stat, args):
    stat_opts = rdf_file_finder.FileFinderStatActionOptions(
        resolve_links=True,
        collect_ext_attrs=args.action.download.collect_ext_attrs)

    stat_entry = self.Stat(fname, stat, stat_opts)
    uploaded_file = self.Upload(fname, stat, args.action.download)
    if uploaded_file:
      uploaded_file.stat_entry = stat_entry

    return rdf_file_finder.FileFinderResult(
        stat_entry=stat_entry, uploaded_file=uploaded_file)

  def _ExecuteHash(self, fname, stat, args):
    stat_opts = rdf_file_finder.FileFinderStatActionOptions(
        resolve_links=True,
        collect_ext_attrs=args.action.hash.collect_ext_attrs)

    stat_entry = self.Stat(fname, stat, stat_opts)
    hash_entry = self.Hash(fname, stat, args.action.hash)
    return rdf_file_finder.FileFinderResult(
        stat_entry=stat_entry, hash_entry=hash_entry)

  def Stat(self, fname, stat, opts):
    if opts.resolve_links and stat.IsSymlink():
      try:
        stat = utils.Stat(fname, follow_symlink=True)
      except OSError:
        return None

    pathspec = rdf_paths.PathSpec(
        pathtype=rdf_paths.PathSpec.PathType.OS,
        path=client_utils.LocalPathToCanonicalPath(fname),
        path_options=rdf_paths.PathSpec.Options.CASE_LITERAL)
    return files.MakeStatResponse(
        stat, pathspec=pathspec, ext_attrs=opts.collect_ext_attrs)

  def Hash(self, fname, stat, opts):
    file_size = stat.GetSize()
    if file_size <= opts.max_size:
      max_hash_size = file_size
    else:
      policy = rdf_file_finder.FileFinderHashActionOptions.OversizedFilePolicy
      if opts.oversized_file_policy == policy.SKIP:
        return None
      elif opts.oversized_file_policy == policy.HASH_TRUNCATED:
        max_hash_size = opts.max_size

    hasher = client_utils_common.MultiHasher(progress=self.Progress)
    try:
      hasher.HashFilePath(fname, max_hash_size)
    except IOError:
      return None
    return hasher.GetHashObject()

  def Upload(self, fname, stat, opts):
    max_bytes = None
    if stat.GetSize() > opts.max_size:
      policy = opts.oversized_file_policy
      policy_enum = opts.OversizedFilePolicy
      if policy == policy_enum.DOWNLOAD_TRUNCATED:
        max_bytes = opts.max_size
      elif policy == policy_enum.SKIP:
        return None
      else:
        raise ValueError("Unknown oversized file policy %s." % int(policy))

    uploaded_file = self.grr_worker.UploadFile(
        open(fname, "rb"),
        opts.upload_token,
        max_bytes=max_bytes,
        network_bytes_limit=self.network_bytes_limit,
        session_id=self.session_id,
        progress_callback=self.Progress)
    return uploaded_file

  def CollectGlobs(self, globs):
    expanded_globs = {}
    for glob in globs:
      initial_component, path = self._SplitInitialPathComponent(
          utils.SmartUnicode(glob))
      expanded_globs.setdefault(initial_component, []).extend(
          self._InterpolateGrouping(path))

    component_tree = {}
    for initial_component, glob_list in expanded_globs.iteritems():
      for glob in glob_list:
        node = component_tree.setdefault(initial_component, {})
        for component in self._ConvertGlobIntoPathComponents(glob):
          node = node.setdefault(component, {})

    for initial_component in component_tree:
      for f in self._TraverseComponentTree(component_tree[initial_component],
                                           initial_component):
        yield f

  def _SplitInitialPathComponent(self, path):
    r"""Splits off the initial component of the given path.

    This function is needed since on Windows, the first component of a
    path (usually indicating a drive) needs to be treated
    specially. Even though there are many ways of specifying paths on
    Windows, we only support the syntax c:\file.

    Args:
      path: The path to split.
    Returns:
      A tuple, first component and remainder.
    Raises:
      ValueError: The path format was not understood.
    """

    if platform.system() != "Windows":
      return u"/", path

    # In case the path start with: C:
    if len(path) >= 2 and path[1] == u":":
      # A backslash is needed after the drive letter to make this an
      # absolute path. Also, we always capitalize the drive letter.
      return path[:2].upper() + u"\\", path[2:].lstrip(u"\\")

    raise ValueError("Can't handle path: %s" % path)

  def _TraverseComponentTree(self, component_tree, base_path):

    for component, subtree in component_tree.iteritems():
      for f in component.Generate(base_path):
        if subtree:
          for res in self._TraverseComponentTree(subtree,
                                                 os.path.join(base_path, f)):
            yield res
        else:
          yield os.path.join(base_path, f)

  def _InterpolateGrouping(self, pattern):
    """Takes the pattern and splits it into components.

    Each grouping pattern is expanded into a set:
      /foo{a,b}/bar -> ["/foo", set(["a", "b"]), "/bar"]

    Raises:
      ValueError: Unknown pattern or interpolation.
      NotImplementedError: The pattern is using knowledgebase interpolations,
                           they are not implemented client side yet.
    Args:
      pattern: list of patterns.
    Returns:
      A list of interpolated patterns.
    """
    result = []
    components = []
    offset = 0
    for match in self.GROUPING_PATTERN.finditer(pattern):
      match_str = match.group(0)
      # Alternatives.
      if match_str.startswith(u"{"):
        components.append([pattern[offset:match.start()]])

        # Expand the attribute into the set of possibilities:
        alternatives = match.group(2).split(u",")
        components.append(set(alternatives))
        offset = match.end()

      # KnowledgeBase interpolation.
      elif match_str.startswith(u"%"):
        raise NotImplementedError("Client side knowledgebase not available.")

      else:
        raise ValueError("Unknown interpolation %s" % match.group(0))

    components.append([pattern[offset:]])
    # Now calculate the cartesian products of all these sets to form all
    # strings.
    for vector in itertools.product(*components):
      result.append(u"".join(vector))

    # These should be all possible patterns.
    # e.g. /fooa/bar , /foob/bar
    return result

  def _ConvertGlobIntoPathComponents(self, pattern):
    r"""Converts a glob pattern into a list of components.

    Wildcards are also converted to regular expressions. The
    components do not span directories, and are marked as a regex or a
    literal component.
    We also support recursion into directories using the ** notation.  For
    example, /home/**2/foo.txt will find all files named foo.txt recursed 2
    directories deep. If the directory depth is omitted, it defaults to 3.
    Example:
     /home/**/*.exe -> [{type: "LITERAL", path: "home"},
                        {type: "RECURSIVE"},
                        {type: "REGEX", path: ".*\\.exe\\Z(?ms)"}]]
    Args:
      pattern: A glob expression with wildcards.
    Returns:
      A list of Components.
    Raises:
      ValueError: If the glob is invalid.
    """
    components = []
    recursion_count = 0
    for path_component in pattern.split(os.path.sep):
      if not path_component:
        continue

      m = self.RECURSION_REGEX.search(path_component)
      if m:
        recursion_count += 1
        if recursion_count > 1:
          raise ValueError("Pattern cannot have more than one recursion.")

        if m.group(0) != path_component:
          raise ValueError("Can't have combined recursive search and regex.")

        depth = 3

        # Allow the user to override the recursion depth.
        if m.group(1):
          depth = int(m.group(1))

        component = RecursiveComponent(
            depth=depth,
            follow_links=self.follow_links,
            mountpoints_blacklist=self.mountpoints_blacklist)

      elif self.GLOB_MAGIC_CHECK.search(path_component):
        component = RegexComponent(fnmatch.translate(path_component))

      else:
        component = LiteralComponent(path_component)

      components.append(component)

    return components


class MetadataCondition(object):
  """An abstract class representing conditions on the file metadata."""

  __metaclass__ = abc.ABCMeta

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
    min_mtime = self.params.min_last_modified_time.AsSecondsFromEpoch()
    max_mtime = self.params.max_last_modified_time.AsSecondsFromEpoch()
    return min_mtime <= stat.GetModificationTime() <= max_mtime


class AccessTimeCondition(MetadataCondition):
  """A condition checking access time of a file."""

  def __init__(self, params):
    super(AccessTimeCondition, self).__init__()
    self.params = params.access_time

  def Check(self, stat):
    min_atime = self.params.min_last_access_time.AsSecondsFromEpoch()
    max_atime = self.params.max_last_access_time.AsSecondsFromEpoch()
    return min_atime <= stat.GetAccessTime() <= max_atime


class InodeChangeTimeCondition(MetadataCondition):
  """A condition checking change time of inode of a file."""

  def __init__(self, params):
    super(InodeChangeTimeCondition, self).__init__()
    self.params = params.inode_change_time

  def Check(self, stat):
    min_ctime = self.params.min_last_inode_change_time.AsSecondsFromEpoch()
    max_ctime = self.params.max_last_inode_change_time.AsSecondsFromEpoch()
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


class ContentCondition(object):
  """An abstract class representing conditions on the file contents."""

  __metaclass__ = abc.ABCMeta

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
    streamer = streaming.FileStreamer(
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


class Matcher(object):
  """An abstract class for objects able to lookup byte strings."""

  __metaclass__ = abc.ABCMeta

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
