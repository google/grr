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


class _SkipFileException(Exception):
  pass


# TODO(hanuszczak): This class should be removed once the new path component
# system is ready.
class _OldComponent(object):
  """A component of a path."""

  def __hash__(self):
    return hash(self.__str__())

  def Generate(self, base_path):
    raise NotImplementedError()


# TODO(hanuszczak): This class should be removed once the new path component
# system is ready.
class _OldRecursiveComponent(_OldComponent):
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


# TODO(hanuszczak): This class should be removed once the new path component
# system is ready.
class _OldRegexComponent(_OldComponent):
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


# TODO(hanuszczak): This class should be removed once the new path component
# system is ready.
class _OldLiteralComponent(_OldComponent):
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

    self.stat_cache = utils.StatCache()

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

    action = self._ParseAction(args)

    for fname in self.CollectGlobs(args.paths):
      self.Progress()
      try:
        matches = self._Validate(args, fname)
        result = rdf_file_finder.FileFinderResult()
        result.matches = matches
        action.Execute(fname, result)
        self.SendReply(result)
      except _SkipFileException:
        pass

  def _ParseAction(self, args):
    action_type = args.action.action_type
    if action_type == rdf_file_finder.FileFinderAction.Action.STAT:
      return StatAction(self, args.action.stat)
    if action_type == rdf_file_finder.FileFinderAction.Action.HASH:
      return HashAction(self, args.action.hash)
    if action_type == rdf_file_finder.FileFinderAction.Action.DOWNLOAD:
      return DownloadAction(self, args.action.download)
    raise ValueError("Incorrect action type: %s" % action_type)

  def _GetStat(self, filepath, follow_symlink=True):
    try:
      return self.stat_cache.Get(filepath, follow_symlink=follow_symlink)
    except OSError:
      raise _SkipFileException()

  def _Validate(self, args, filepath):
    matches = []
    self._ValidateRegularity(args, filepath)
    self._ValidateMetadata(args, filepath)
    self._ValidateContent(args, filepath, matches)
    return matches

  def _ValidateRegularity(self, args, filepath):
    stat = self._GetStat(filepath, follow_symlink=False)

    is_regular = stat.IsRegular() or stat.IsDirectory()
    if not is_regular and not args.process_non_regular_files:
      raise _SkipFileException()

  def _ValidateMetadata(self, args, filepath):
    stat = self._GetStat(filepath, follow_symlink=False)

    for metadata_condition in MetadataCondition.Parse(args.conditions):
      if not metadata_condition.Check(stat):
        raise _SkipFileException()

  def _ValidateContent(self, args, filepath, matches):
    for content_condition in ContentCondition.Parse(args.conditions):
      result = list(content_condition.Search(filepath))
      if not result:
        raise _SkipFileException()
      matches.extend(result)

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

        component = _OldRecursiveComponent(
            depth=depth,
            follow_links=self.follow_links,
            mountpoints_blacklist=self.mountpoints_blacklist)

      elif self.GLOB_MAGIC_CHECK.search(path_component):
        component = _OldRegexComponent(fnmatch.translate(path_component))

      else:
        component = _OldLiteralComponent(path_component)

      components.append(component)

    return components


class PathOpts(object):
  """Options used for path expansion.

  This is a convenience class used to avoid threading multiple default
  parameters in glob expansion functions.

  Args:
    follow_links: Whether glob expansion mechanism should follow symlinks.
    recursion_blacklist: List of folders that the glob expansion should not
                         recur to.
  """

  def __init__(self, follow_links=False, recursion_blacklist=None):
    self.follow_links = follow_links
    self.recursion_blacklist = set(recursion_blacklist or [])


class PathComponent(object):
  """An abstract class representing parsed path component.

  A path component is part of the path delimited by the directory separator.
  """

  __metaclass__ = abc.ABCMeta

  @abc.abstractmethod
  def Generate(self, dirpath):
    """Yields children of a given directory matching the component."""


class RecursiveComponent(PathComponent):
  """A class representing recursive path components.

  A recursive component (specified as `**`) matches any directory tree up to
  some specified depth (3 by default).

  Attributes:
    max_depth: Maximum depth of the recursion for directory discovery.
    opts: A `PathOpts` object.
  """

  DEFAULT_MAX_DEPTH = 3

  def __init__(self, max_depth=None, opts=None):
    super(RecursiveComponent, self).__init__()
    self.max_depth = max_depth or self.DEFAULT_MAX_DEPTH
    self.opts = opts or PathOpts()

  def Generate(self, dirpath):
    return self._Generate(dirpath, 1)

  def _Generate(self, dirpath, depth):
    if depth > self.max_depth:
      return

    for item in _ListDir(dirpath):
      itempath = os.path.join(dirpath, item)
      yield itempath

      if itempath in self.opts.recursion_blacklist:
        continue
      for childpath in self._Recurse(itempath, depth):
        yield childpath

  def _Recurse(self, path, depth):
    if not os.path.isdir(path):
      return
    if not self.opts.follow_links and os.path.islink(path):
      return
    for childpath in self._Generate(path, depth + 1):
      yield childpath


class GlobComponent(PathComponent):
  """A class representing glob path components.

  A glob component can use wildcards and character sets that match particular
  strings. For more information see man page for `glob`.

  Note that regular names (such as `foo`) are special case of a glob components
  that contain no wildcards and match only themselves.

  Attributes:
    glob: A string with potential glob elements (e.g. `foo*`).
  """

  def __init__(self, glob):
    super(GlobComponent, self).__init__()
    self.regex = re.compile(fnmatch.translate(glob), re.I)

  def Generate(self, dirpath):
    for item in _ListDir(dirpath):
      if self.regex.match(item):
        yield os.path.join(dirpath, item)


class CurrentComponent(PathComponent):
  """A class representing current directory components.

  A current directory is a path component that corresponds to the `.` (dot)
  symbol on most systems. Technically it expands to nothing but it is useful
  with group expansion mechanism.
  """

  def Generate(self, dirpath):
    yield dirpath


class ParentComponent(PathComponent):
  """A class representing parent directory components.

  A parent directory is a path component that corresponds to the `..` (double
  dot) symbol on most systems. It allows to go one directory up in the hierarchy
  and is an useful tool with group expansion.
  """

  def Generate(self, dirpath):
    yield os.path.dirname(dirpath)


PATH_PARAM_REGEX = re.compile("%%(?P<name>[^%]+?)%%")
PATH_GROUP_REGEX = re.compile("{(?P<alts>[^}]+,[^}]+)}")
PATH_RECURSION_REGEX = re.compile(r"\*\*(?P<max_depth>\d*)")


def ParsePathItem(item, opts=None):
  """Parses string path component to an `PathComponent` instance.

  Args:
    item: A path component string to be parsed.
    opts: A `PathOpts` object.

  Returns:
    `PathComponent` instance corresponding to given path fragment.

  Raises:
    ValueError: If the path item contains a recursive component fragment but
      cannot be parsed as such.
  """
  if item == os.path.curdir:
    return CurrentComponent()

  if item == os.path.pardir:
    return ParentComponent()

  recursion = PATH_RECURSION_REGEX.search(item)
  if not recursion:
    return GlobComponent(item)

  start, end = recursion.span()
  if not (start == 0 and end == len(item)):
    raise ValueError("malformed recursive component")

  if recursion.group("max_depth"):
    max_depth = int(recursion.group("max_depth"))
  else:
    max_depth = None

  return RecursiveComponent(max_depth=max_depth, opts=opts)


def ParsePath(path, opts=None):
  """Parses given path into a stream of `PathComponent` instances.

  Args:
    path: A path to be parsed.
    opts: An `PathOpts` object.

  Yields:
    `PathComponent` instances corresponding to the components of the given path.

  Raises:
    ValueError: If path contains more than one recursive component.
  """
  rcount = 0
  for item in path.split(os.path.sep):
    component = ParsePathItem(item, opts=opts)
    if isinstance(component, RecursiveComponent):
      rcount += 1
      if rcount > 1:
        raise ValueError("path cannot have more than one recursive component")
    yield component


def ExpandPath(path, opts=None):
  """Applies all expansion mechanisms to the given path.

  Args:
    path: A path to expand.
    opts: A `PathOpts` object.

  Yields:
    All paths possible to obtain from a given path by performing expansions.
  """
  parametrized_path = ExpandParams(path)
  for grouped_path in ExpandGroups(parametrized_path):
    for globbed_path in ExpandGlobs(grouped_path, opts=opts):
      yield globbed_path


# TODO(hanuszczak): Implement parameter expansion of client-side file-finder.
# Future request for this is here: https://github.com/google/grr/issues/548.
def ExpandParams(path):
  """Performs path parameter interpolation.

  Args:
    path: A path to expand.

  Returns:
    A path with all parameters interpolated according to the knowledgebase.

  Raises:
    NotImplementedError: If the path contains a parameter since parameter
                         interpolation is not implemented yet.
  """
  for match in PATH_PARAM_REGEX.finditer(path):
    del match  # Unused.
    raise NotImplementedError("Client-side parameter expansion not supported")
  return path


def ExpandGroups(path):
  """Performs group expansion on a given path.

  For example, given path `foo/{bar,baz}/{quux,norf}` this method will yield
  `foo/bar/quux`, `foo/bar/norf`, `foo/baz/quux`, `foo/baz/norf`.

  Args:
    path: A path to expand.

  Yields:
    Paths that can be obtained from given path by expanding groups.
  """
  chunks = []
  offset = 0

  for match in PATH_GROUP_REGEX.finditer(path):
    chunks.append([path[offset:match.start()]])
    chunks.append(match.group("alts").split(","))
    offset = match.end()

  chunks.append([path[offset:]])

  for prod in itertools.product(*chunks):
    yield "".join(prod)


def ExpandGlobs(path, opts=None):
  """Performs glob expansion on a given path.

  Path can contain regular glob elements (such as `**`, `*`, `?`, `[a-z]`). For
  example, having files `foo`, `bar`, `baz` glob expansion of `ba?` will yield
  `bar` and `baz`.

  Args:
    path: A path to expand.
    opts: A `PathOpts` object.

  Returns:
    Generator over all possible glob expansions of a given path.

  Raises:
    ValueError: If given path is empty or relative.
  """
  if not path:
    raise ValueError("Path is empty")

  root, path = os.path.splitdrive(path)
  if not root:
    if path[0] != "/":
      raise ValueError("Path '%s' is not absolute" % path)
    root, path = path[0], path[1:]

  components = list(ParsePath(path, opts=opts))
  return _ExpandComponents(root.upper(), components)


def _ExpandComponents(basepath, components, index=0):
  if index == len(components):
    yield basepath
    return

  for childpath in components[index].Generate(basepath):
    for path in _ExpandComponents(childpath, components, index + 1):
      yield path


def _ListDir(dirpath):
  """Returns children of a given directory.

  This function is intended to be used by the `PathComponent` subclasses to get
  initial list of potential children that then need to be filtered according to
  the rules of a specific component.

  Args:
    dirpath: A path to the directory.
  """
  try:
    return os.listdir(dirpath)
  except OSError as error:
    if error.errno == errno.EACCES:
      logging.info(error)
    return []


# TODO(hanuszczak): Move subaction classes to a separate module.


class Action(object):
  """An abstract class for subactions of the client-side file-finder.

  Attributes:
    flow: A parent flow action that spawned the subaction.
  """

  __metaclass__ = abc.ABCMeta

  def __init__(self, flow):
    self.flow = flow

  @abc.abstractmethod
  def Execute(self, filepath, result):
    """Executes the action on a given path.

    Concrete action implementations should return results by filling-in
    appropriate fields of the result instance.

    Args:
      filepath: A path to the file on which the action is going to be performed.
      result: An `FileFinderResult` instance to fill-in.
    """
    pass


class StatAction(Action):
  """Implementation of the stat subaction.

  This subaction just gathers basic metadata information about the specified
  file (such as size, modification time, extended attributes and flags.

  Attributes:
    flow: A parent flow action that spawned the subaction.
    opts: A `FileFinderStatActionOptions` instance.
  """

  def __init__(self, flow, opts):
    super(StatAction, self).__init__(flow)
    self.opts = opts

  def Execute(self, filepath, result):
    stat_cache = self.flow.stat_cache

    stat = stat_cache.Get(filepath, follow_symlink=self.opts.resolve_links)
    result.stat_entry = _StatEntry(stat, ext_attrs=self.opts.collect_ext_attrs)


class HashAction(Action):
  """Implementation of the hash subaction.

  This subaction returns results of various hashing algorithms applied to the
  specified file. Additionally it also gathers basic information about the
  hashed file.

  Attributes:
    flow: A parent flow action that spawned the subaction.
    opts: A `FileFinderHashActionOptions` instance.
  """

  def __init__(self, flow, opts):
    super(HashAction, self).__init__(flow)
    self.opts = opts

  def Execute(self, filepath, result):
    stat = self.flow.stat_cache.Get(filepath, follow_symlink=True)
    result.stat_entry = _StatEntry(stat, ext_attrs=self.opts.collect_ext_attrs)

    if stat.IsDirectory():
      return

    policy = self.opts.oversized_file_policy
    max_size = self.opts.max_size
    if stat.GetSize() <= self.opts.max_size:
      result.hash_entry = _HashEntry(stat, self.flow)
    elif policy == self.opts.OversizedFilePolicy.HASH_TRUNCATED:
      result.hash_entry = _HashEntry(stat, self.flow, max_size=max_size)
    elif policy == self.opts.OversizedFilePolicy.SKIP:
      return
    else:
      raise ValueError("Unknown oversized file policy: %s" % policy)


class DownloadAction(Action):
  """Implementation of the download subaction.

  This subaction sends a specified file to the server and returns a handle to
  its stored version. Additionally it also gathers basic metadata about the
  file.

  Attributes:
    flow: A parent flow action that spawned the subaction.
    opts: A `FileFinderDownloadActionOptions` instance.
  """

  def __init__(self, flow, opts):
    super(DownloadAction, self).__init__(flow)
    self.opts = opts

  def Execute(self, filepath, result):
    stat = self.flow.stat_cache.Get(filepath, follow_symlink=True)
    result.stat_entry = _StatEntry(stat, ext_attrs=self.opts.collect_ext_attrs)

    if stat.IsDirectory():
      return

    policy = self.opts.oversized_file_policy
    max_size = self.opts.max_size
    if stat.GetSize() <= max_size:
      result.uploaded_file = self._UploadFilePath(filepath)
      result.uploaded_file.stat_entry = result.stat_entry
    elif policy == self.opts.OversizedFilePolicy.DOWNLOAD_TRUNCATED:
      result.uploaded_file = self._UploadFilePath(filepath, truncate=True)
      result.uploaded_file.stat_entry = result.stat_entry
    elif policy == self.opts.OversizedFilePolicy.HASH_TRUNCATED:
      result.hash_entry = _HashEntry(stat, self.flow, max_size=max_size)
    elif policy == self.opts.OversizedFilePolicy.SKIP:
      return
    else:
      raise ValueError("Unknown oversized file policy: %s" % policy)

  def _UploadFilePath(self, filepath, truncate=False):
    with open(filepath, "rb") as fdesc:
      return self._UploadFile(fdesc, truncate=truncate)

  def _UploadFile(self, fdesc, truncate=False):
    max_size = self.opts.max_size if truncate else None
    return self.flow.grr_worker.UploadFile(
        fdesc,
        self.opts.upload_token,
        max_bytes=max_size,
        network_bytes_limit=self.flow.network_bytes_limit,
        session_id=self.flow.session_id,
        progress_callback=self.flow.Progress)


def _StatEntry(stat, ext_attrs):
  pathspec = rdf_paths.PathSpec(
      pathtype=rdf_paths.PathSpec.PathType.OS,
      path=client_utils.LocalPathToCanonicalPath(stat.GetPath()),
      path_options=rdf_paths.PathSpec.Options.CASE_LITERAL)
  return files.MakeStatResponse(stat, pathspec=pathspec, ext_attrs=ext_attrs)


def _HashEntry(stat, flow, max_size=None):
  hasher = client_utils_common.MultiHasher(progress=flow.Progress)
  try:
    hasher.HashFilePath(stat.GetPath(), max_size or stat.GetSize())
    return hasher.GetHashObject()
  except IOError:
    return None


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
