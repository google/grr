#!/usr/bin/env python
"""Implementation of path expansion mechanism for client-side file-finder."""

import abc
import errno
import fnmatch
import itertools
import logging
import os
import platform
import re


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
  for grouped_path in ExpandGroups(path):
    for globbed_path in ExpandGlobs(grouped_path, opts=opts):
      yield globbed_path


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

  drive, tail = os.path.splitdrive(path)
  if ((platform.system() == "Windows" and not drive) or
      not (tail and tail[0] == os.path.sep)):
    raise ValueError("Path '%s' is not absolute" % path)
  root_dir = os.path.join(drive, os.path.sep).upper()
  components = list(ParsePath(tail[1:], opts=opts))
  return _ExpandComponents(root_dir, components)


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
