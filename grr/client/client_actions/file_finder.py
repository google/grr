#!/usr/bin/env python
"""The file finder client action."""

import collections
import errno
import fnmatch
import functools
import itertools
import logging
import os
import platform
import re
import stat

import psutil

from grr.client import actions
from grr.client import client_utils
from grr.client import client_utils_common
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
      if len(new_components) < self.depth:
        try:
          filename = os.path.join(base_path, relative_name)
          stat_entry = os.stat(filename)
          if stat.S_ISDIR(stat_entry.st_mode):
            if filename in self.mountpoints_blacklist:
              continue
            if (self.follow_links or
                not stat.S_ISLNK(os.lstat(filename).st_mode)):
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

      try:
        stat_object = os.lstat(fname)
      except OSError:
        continue

      if (not self.process_non_regular_files and
          not stat.S_ISDIR(stat_object.st_mode) and
          not stat.S_ISREG(stat_object.st_mode)):
        continue

      matches = []

      # `all` lazily evaluates the generator expresion until first failure.
      conditions = self.ParseConditions(args)
      if not all(cond(fname, stat_object, matches) for cond in conditions):
        continue

      result = self._ProcessFile(fname, stat_object, args)
      if result:
        result.matches = matches
        self.SendReply(result)

  def _ProcessFile(self, fname, stat_object, args):
    if args.action.action_type == args.action.Action.STAT:
      return self._ExecuteStat(fname, stat_object, args)

    # For directories, only Stat makes sense.
    if stat.S_ISDIR(stat_object.st_mode):
      return None

    # We never want to hash/download the link, always the target.
    if stat.S_ISLNK(stat_object.st_mode):
      try:
        stat_object = os.stat(fname)
      except OSError:
        return None

    if args.action.action_type == args.action.Action.DOWNLOAD:
      return self._ExecuteDownload(fname, stat_object, args)

    if args.action.action_type == args.action.Action.HASH:
      return self._ExecuteHash(fname, stat_object, args)

    raise ValueError("incorrect action type: %s" % args.action.action_type)

  def _ExecuteStat(self, fname, stat_object, args):
    stat_entry = self.Stat(fname, stat_object, args.action.stat.resolve_links)

    return rdf_file_finder.FileFinderResult(stat_entry=stat_entry)

  def _ExecuteDownload(self, fname, stat_object, args):
    stat_entry = self.Stat(fname, stat_object, True)
    uploaded_file = self.Upload(fname, stat_object, args.action.download,
                                args.upload_token)
    if uploaded_file:
      uploaded_file.stat_entry = stat_entry

    return rdf_file_finder.FileFinderResult(
        stat_entry=stat_entry, uploaded_file=uploaded_file)

  def _ExecuteHash(self, fname, stat_object, args):
    stat_entry = self.Stat(fname, stat_object, True)
    hash_entry = self.Hash(fname, stat_object, args.action.hash)

    return rdf_file_finder.FileFinderResult(
        stat_entry=stat_entry, hash_entry=hash_entry)

  def Stat(self, fname, stat_object, resolve_links):
    if resolve_links and stat.S_ISLNK(stat_object.st_mode):
      try:
        stat_object = os.stat(fname)
      except OSError:
        return None

    pathspec = rdf_paths.PathSpec(
        pathtype=rdf_paths.PathSpec.PathType.OS,
        path=client_utils.LocalPathToCanonicalPath(fname),
        path_options=rdf_paths.PathSpec.Options.CASE_LITERAL)
    return files.MakeStatResponse(stat_object, pathspec=pathspec)

  def Hash(self, fname, stat_object, opts):
    file_size = stat_object.st_size
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

  def Upload(self, fname, stat_object, opts, token):
    max_bytes = None
    if stat_object.st_size > opts.max_size:
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
        token,
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

  @staticmethod
  def ModificationTimeCondition(condition_obj, path, stat_obj, matches):
    del matches  # Unused.

    params = condition_obj.modification_time
    min_mtime = params.min_last_modified_time.AsSecondsFromEpoch()
    max_mtime = params.max_last_modified_time.AsSecondsFromEpoch()
    return min_mtime <= stat_obj.st_mtime <= max_mtime

  @staticmethod
  def AccessTimeCondition(condition_obj, path, stat_obj, matches):
    del matches  # Unused.

    params = condition_obj.access_time
    min_atime = params.min_last_access_time.AsSecondsFromEpoch()
    max_atime = params.max_last_access_time.AsSecondsFromEpoch()
    return min_atime <= stat_obj.st_atime <= max_atime

  @staticmethod
  def InodeChangeTimeCondition(condition_obj, path, stat_obj, matches):
    del matches  # Unused.

    params = condition_obj.inode_change_time
    min_ctime = params.min_last_inode_change_time.AsSecondsFromEpoch()
    max_ctime = params.max_last_inode_change_time.AsSecondsFromEpoch()
    return min_ctime <= stat_obj.st_ctime <= max_ctime

  @staticmethod
  def SizeCondition(condition_obj, path, stat_obj, matches):
    del matches  # Unused.

    params = condition_obj.size
    return params.min_file_size <= stat_obj.st_size <= params.max_file_size

  OVERLAP_SIZE = 1024 * 1024
  CHUNK_SIZE = 10 * 1024 * 1024

  @staticmethod
  def _StreamFile(fd, offset, length):
    """Generates overlapping blocks of data read from a file."""
    to_read = length
    fd.seek(offset)

    overlap = fd.read(min(FileFinderOS.OVERLAP_SIZE, to_read))
    to_read -= len(overlap)

    yield overlap

    while to_read > 0:
      data = fd.read(min(FileFinderOS.CHUNK_SIZE, to_read))
      if not data:
        return
      to_read -= len(data)

      combined_data = overlap + data
      yield combined_data
      overlap = combined_data[-FileFinderOS.OVERLAP_SIZE:]

  @staticmethod
  def _MatchRegex(regex, chunk, pos):
    match = regex.Search(chunk[pos:])
    if not match:
      return None, 0
    else:
      start, end = match.span()
      return start + pos, end - start

  @staticmethod
  def ContentsRegexMatchCondition(condition_obj, path, stat_obj, matches):
    params = condition_obj.contents_regex_match
    regex = params.regex

    matching = functools.partial(FileFinderOS._MatchRegex, regex)
    return FileFinderOS._ScanForMatches(params, path, matching, matches)

  @staticmethod
  def _MatchLiteral(literal, chunk, pos):
    pos = chunk.find(literal, pos)
    if pos == -1:
      return None, 0
    else:
      return pos, len(literal)

  @staticmethod
  def ContentsLiteralMatchCondition(condition_obj, path, stat_obj, matches):
    params = condition_obj.contents_literal_match

    literal = utils.SmartStr(params.literal)

    matching = functools.partial(FileFinderOS._MatchLiteral, literal)
    return FileFinderOS._ScanForMatches(params, path, matching, matches)

  @staticmethod
  def _ScanForMatches(params, path, matching_func, matches):
    try:
      fd = open(path, mode="rb")
    except IOError:
      return False

    current_offset = params.start_offset
    findings = []
    for chunk in FileFinderOS._StreamFile(fd, current_offset, params.length):
      pos, match_length = matching_func(chunk, 0)
      while pos is not None:
        if (len(chunk) > FileFinderOS.OVERLAP_SIZE and
            pos + match_length < FileFinderOS.OVERLAP_SIZE):
          # We already processed this hit.
          pos, match_length = matching_func(chunk, pos + 1)
          continue

        context_start = max(pos - params.bytes_before, 0)
        # This might cut off some data if the hit is at the chunk border.
        context_end = min(pos + match_length + params.bytes_after, len(chunk))
        data = chunk[context_start:context_end]
        findings.append(
            rdf_client.BufferReference(
                offset=current_offset + context_start,
                length=len(data),
                data=data,
            ))
        if params.mode == params.Mode.FIRST_HIT:
          for finding in findings:
            matches.append(finding)
          return True

        pos, match_length = matching_func(chunk, pos + 1)

      current_offset += len(chunk) - FileFinderOS.OVERLAP_SIZE

    if findings:
      for finding in findings:
        matches.append(finding)
      return True
    else:
      return False

  _CONDITION_DESCRIPTOR = collections.namedtuple("ConditionDescriptor",
                                                 ["weight", "handler"])

  _CONDITION_TYPE = rdf_file_finder.FileFinderCondition.Type

  _CONDITIONS = {
      _CONDITION_TYPE.MODIFICATION_TIME:
          _CONDITION_DESCRIPTOR(weight=0, handler=ModificationTimeCondition),
      _CONDITION_TYPE.ACCESS_TIME:
          _CONDITION_DESCRIPTOR(weight=0, handler=AccessTimeCondition),
      _CONDITION_TYPE.INODE_CHANGE_TIME:
          _CONDITION_DESCRIPTOR(weight=0, handler=InodeChangeTimeCondition),
      _CONDITION_TYPE.SIZE:
          _CONDITION_DESCRIPTOR(weight=0, handler=SizeCondition),
      _CONDITION_TYPE.CONTENTS_REGEX_MATCH:
          _CONDITION_DESCRIPTOR(weight=1, handler=ContentsRegexMatchCondition),
      _CONDITION_TYPE.CONTENTS_LITERAL_MATCH:
          _CONDITION_DESCRIPTOR(
              weight=1, handler=ContentsLiteralMatchCondition),
  }

  @staticmethod
  def _GetConditionWeight(cond):
    return FileFinderOS._CONDITIONS[cond.condition_type].weight

  @staticmethod
  def _GetConditionHandler(cond):
    handler = FileFinderOS._CONDITIONS[cond.condition_type].handler
    return functools.partial(handler.__func__, cond)

  def ParseConditions(self, args):
    conditions = sorted(args.conditions, key=self._GetConditionWeight)
    return map(self._GetConditionHandler, conditions)
