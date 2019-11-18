#!/usr/bin/env python
"""Implementation of path expansion mechanism for client-side file-finder."""
from __future__ import absolute_import
from __future__ import division

from __future__ import print_function
from __future__ import unicode_literals

import abc
import itertools
import os
import platform
import re
import stat

from future.utils import with_metaclass
import psutil
from typing import Callable, Iterator, Optional, Text

from grr_response_client import vfs
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.util import precondition
from grr_response_core.lib.util.compat import fnmatch


def _NoOp():
  """Does nothing. This function is to be used as default heartbeat callback."""


class PathOpts(object):
  """Options used for path expansion.

  This is a convenience class used to avoid threading multiple default
  parameters in glob expansion functions.

  Args:
    follow_links: Whether glob expansion mechanism should follow symlinks.
    xdev: Xdev flag as specified in the FileFinderArgs protobuf. If unset,
      defaults to ALWAYS.
    pathtype: The pathtype to use.
  """

  def __init__(self, follow_links=False, xdev=None, pathtype=None):
    self.follow_links = follow_links
    self.pathtype = pathtype or rdf_paths.PathSpec.PathType.OS
    if xdev is None:
      self.xdev = rdf_file_finder.FileFinderArgs.XDev.ALWAYS
    else:
      self.xdev = xdev

  def __repr__(self):
    raw = "PathOpts(follow_links={}, xdev={}, pathtype={})"
    return raw.format(bool(self.follow_links), self.xdev, self.pathtype)


class PathComponent(with_metaclass(abc.ABCMeta, object)):
  """An abstract class representing parsed path component.

  A path component is part of the path delimited by the directory separator.
  """

  @abc.abstractmethod
  def Generate(self, dirpath):
    """Yields children of a given directory matching the component."""


class RecursiveComponent(PathComponent):
  """A class representing recursive path components.

  A recursive component (specified as `**`) matches any directory tree up to
  some specified depth (3 by default). ** does not match the current directory.

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
    self.allowed_devices = _GetAllowedDevices(self.opts.xdev, dirpath)
    return self._Generate(dirpath, 1)

  def _Generate(self, dirpath, depth):
    if depth > self.max_depth:
      return

    for item in _ListDir(dirpath, self.opts.pathtype):
      itempath = os.path.join(dirpath, item)

      yield itempath

      for childpath in self._Recurse(itempath, depth):
        yield childpath

  def _Recurse(self, path, depth):
    if self.opts.pathtype == rdf_paths.PathSpec.PathType.OS:
      try:
        stat_entry = os.stat(path)
      except OSError:
        # Can happen for links pointing to non existent files/directories.
        return

      if (self.allowed_devices is not _XDEV_ALL_ALLOWED and
          stat_entry.st_dev not in self.allowed_devices):
        return

      if not stat.S_ISDIR(stat_entry.st_mode):
        return

      # Cannot use S_ISLNK here because we uses os.stat above which resolves
      # links.
      if not self.opts.follow_links and os.path.islink(path):
        return

    elif self.opts.pathtype == rdf_paths.PathSpec.PathType.REGISTRY:
      pathspec = rdf_paths.PathSpec(
          path=path, pathtype=rdf_paths.PathSpec.PathType.REGISTRY)
      try:
        with vfs.VFSOpen(pathspec) as filedesc:
          if not filedesc.IsDirectory():
            return
      except IOError:
        return  # Skip inaccessible Registry parts (e.g. HKLM\SAM\SAM) silently.
    else:
      raise AssertionError("Invalid pathtype {}".format(self.opts.pathtype))

    for childpath in self._Generate(path, depth + 1):
      yield childpath

  def __repr__(self):
    return "RecursiveComponent(max_depth={}, opts={!r})".format(
        self.max_depth, self.opts)


class GlobComponent(PathComponent):
  """A class representing glob path components.

  A glob component can use wildcards and character sets that match particular
  strings. For more information see man page for `glob`.

  Note that regular names (such as `foo`) are special case of a glob components
  that contain no wildcards and match only themselves.
  """

  def __init__(self, glob, opts = None):
    """Instantiates a new GlobComponent from a given path glob.

    Args:
      glob: A string with potential glob elements (e.g. `foo*`).
      opts: An optional PathOpts instance.
    """
    super(GlobComponent, self).__init__()
    self._glob = glob
    self._is_literal = PATH_GLOB_REGEX.search(self._glob) is None
    self.regex = re.compile(fnmatch.translate(glob), re.I)
    self.opts = opts or PathOpts()

  def _GenerateLiteralMatchOS(self, dirpath):
    if not os.path.exists(os.path.join(dirpath, self._glob)):
      return None

    if platform.system() != "Windows":
      return self._glob

    # On Windows, we are able to open the path even if the casing does not match
    # so we need to perform an additional case correction step.  TODO(amoser):
    # The best way to do this is probably using Python3's pathlib:
    # https://stackoverflow.com/questions/3692261/in-python-how-can-i-get-the-correctly-cased-path-for-a-file/14742779
    # but that solution is Python3 only. For now do this the slow way, once we
    # drop Python2 support for good, we can switch to pathlib instead.

    lower_glob = self._glob.lower()
    for fname in os.listdir(dirpath):
      if fname.lower() == lower_glob:
        return fname
    return None

  def _GenerateLiteralMatch(self, dirpath):
    if self.opts.pathtype == rdf_paths.PathSpec.PathType.OS:
      return self._GenerateLiteralMatchOS(dirpath)

    new_path = os.path.join(dirpath, self._glob)
    # TODO(amoser): This pathspec should have path_options CASE_LITERAL set such
    # that the VFSOpen call below becomes much faster. Tests show that there is
    # an unicode issue with CASE_LITERAL that we need to fix before adding that
    # option.
    pathspec = rdf_paths.PathSpec(path=new_path, pathtype=self.opts.pathtype)
    try:
      with vfs.VFSOpen(pathspec) as filedesc:
        if filedesc.path == "/" and new_path != "/":
          # TODO: VFSHandler has path = "/" as default. Thus, if we
          # encounter "/", it could either mean the path never has been assigned
          # or the path is literally "/". Thus, we return None if the path is
          # "/" because it has never been set, by cross-referencing with the
          # path we glob for.
          return None
        else:
          return os.path.basename(filedesc.path)
    except IOError:
      return None  # Indicate "File not found" by returning None.

  def Generate(self, dirpath):
    # TODO: The TSK implementation for VFS currently cannot list
    # the root path of mounted disks. To make VfsFileFinder work with TSK,
    # we try the literal match to allow VfsFileFinder to traverse into disk
    # images.

    if self._is_literal:
      literal_match = self._GenerateLiteralMatch(dirpath)
      if literal_match is not None:
        yield os.path.join(dirpath, literal_match)
        return

    for item in _ListDir(dirpath, self.opts.pathtype):
      if self.regex.match(item):
        yield os.path.join(dirpath, item)

  def __repr__(self):
    return "GlobComponent(glob={!r} opts={!r})".format(self._glob, self.opts)


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
# Match strings with patterns that would be translated by fnmatch.translate().
PATH_GLOB_REGEX = re.compile(r"\*|\?|\[.+\]")


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
  if recursion is None:
    return GlobComponent(item, opts)

  start, end = recursion.span()
  if not (start == 0 and end == len(item)):
    raise ValueError("malformed recursive component")

  if recursion.group("max_depth"):
    max_depth = int(recursion.group("max_depth"))
  else:
    max_depth = None

  return RecursiveComponent(max_depth=max_depth, opts=opts)


def ParsePath(path,
              opts = None):
  """Parses given path into a stream of `PathComponent` instances.

  Args:
    path: A path to be parsed.
    opts: An `PathOpts` object.

  Yields:
    `PathComponent` instances corresponding to the components of the given path.

  Raises:
    ValueError: If path contains more than one recursive component.
  """
  precondition.AssertType(path, Text)

  rcount = 0

  # Split the path at all forward slashes and if running under Windows, also
  # backward slashes. This allows ParsePath to handle native paths and also
  # normalized VFS paths like /HKEY_LOCAL_MACHINE/SAM.
  normalized_path = path.replace(os.path.sep, "/")

  for item in normalized_path.split("/"):
    component = ParsePathItem(item, opts=opts)
    if isinstance(component, RecursiveComponent):
      rcount += 1
      if rcount > 1:
        raise ValueError("path cannot have more than one recursive component")
    yield component


def ExpandPath(path,
               opts = None,
               heartbeat_cb = _NoOp):
  """Applies all expansion mechanisms to the given path.

  Args:
    path: A path to expand.
    opts: A `PathOpts` object.
    heartbeat_cb: A function to be called regularly to send heartbeats.

  Yields:
    All paths possible to obtain from a given path by performing expansions.
  """
  precondition.AssertType(path, Text)

  for grouped_path in ExpandGroups(path):
    for globbed_path in ExpandGlobs(grouped_path, opts, heartbeat_cb):
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
  precondition.AssertType(path, Text)

  chunks = []
  offset = 0

  for match in PATH_GROUP_REGEX.finditer(path):
    chunks.append([path[offset:match.start()]])
    chunks.append(match.group("alts").split(","))
    offset = match.end()

  chunks.append([path[offset:]])

  for prod in itertools.product(*chunks):
    yield "".join(prod)


def ExpandGlobs(path,
                opts = None,
                heartbeat_cb = _NoOp):
  """Performs glob expansion on a given path.

  Path can contain regular glob elements (such as `**`, `*`, `?`, `[a-z]`). For
  example, having files `foo`, `bar`, `baz` glob expansion of `ba?` will yield
  `bar` and `baz`.

  Args:
    path: A path to expand.
    opts: A `PathOpts` object.
    heartbeat_cb: A function to be called regularly to send heartbeats.

  Returns:
    Generator over all possible glob expansions of a given path.

  Raises:
    ValueError: If given path is empty or relative.
  """
  precondition.AssertType(path, Text)
  if not path:
    raise ValueError("Path is empty")

  if not _IsAbsolutePath(path, opts):
    raise ValueError("Path '%s' is not absolute" % path)

  if opts is not None and opts.pathtype == rdf_paths.PathSpec.PathType.REGISTRY:
    # Handle HKLM\Foo and /HKLM/Foo identically.
    root_dir, tail = path.replace("\\", "/").lstrip("/").split("/", 1)
    components = list(ParsePath(tail, opts=opts))
  else:
    drive, tail = os.path.splitdrive(path)
    root_dir = os.path.join(drive, os.path.sep).upper()
    components = list(ParsePath(tail[1:], opts=opts))

  return _ExpandComponents(root_dir, components, heartbeat_cb=heartbeat_cb)


def _IsAbsolutePath(path, opts = None):
  if opts and opts.pathtype == rdf_paths.PathSpec.PathType.REGISTRY:
    return path.startswith("/HKEY_") or path.startswith("HKEY_")

  drive, tail = os.path.splitdrive(path)
  if platform.system() == "Windows":
    return bool(drive)

  return bool(tail) and tail[0] == os.path.sep


def _ExpandComponents(basepath, components, index=0, heartbeat_cb=_NoOp):
  heartbeat_cb()

  if index == len(components):
    yield basepath
    return
  for childpath in components[index].Generate(basepath):
    for path in _ExpandComponents(childpath, components, index + 1,
                                  heartbeat_cb):
      yield path


def _ListDir(dirpath, pathtype):
  """Returns children of a given directory.

  This function is intended to be used by the `PathComponent` subclasses to get
  initial list of potential children that then need to be filtered according to
  the rules of a specific component.

  Args:
    dirpath: A path to the directory.
    pathtype: The pathtype to use.

  Raises:
    ValueError: in case of unsupported path types.
  """
  if pathtype == rdf_paths.PathSpec.PathType.OS:
    try:
      return os.listdir(dirpath)
    except OSError:
      return []

  pathspec = rdf_paths.PathSpec(path=dirpath, pathtype=pathtype)
  childpaths = []
  try:
    with vfs.VFSOpen(pathspec) as filedesc:
      for path in filedesc.ListNames():
        # For Windows registry, ignore the empty string which corresponds to the
        # default value in the current key. Otherwise, globbing a key will yield
        # the key itself, because joining the name of the default value u"" with
        # a key name yields the key name again.
        if pathtype != rdf_paths.PathSpec.PathType.REGISTRY or path:
          childpaths.append(path)
  except IOError:
    pass

  return childpaths


def _GetMountpoints(only_physical=True):
  """Fetches a list of mountpoints.

  Args:
    only_physical: Determines whether only mountpoints for physical devices
      (e.g. hard disks) should be listed. If false, mountpoints for things such
      as memory partitions or `/dev/shm` will be returned as well.

  Returns:
    A set of mountpoints.
  """
  partitions = psutil.disk_partitions(all=not only_physical)
  return set(partition.mountpoint for partition in partitions)


_XDEV_ALL_ALLOWED = object()


def _GetAllowedDevices(xdev, path):
  """Builds a list of allowed device IDs we are allowed to recurse into.

  Args:
    xdev: A `XDev` value that determines policy for crossing device boundaries.
    path: The starting path for the recursion.

  Returns:
    A set of allowed device ids or None if there are no restrictions.

  Raises:
    ValueError: If `xdev` value is invalid.
  """
  if xdev == rdf_file_finder.FileFinderArgs.XDev.ALWAYS:
    # Never stop at any device boundary.
    return _XDEV_ALL_ALLOWED

  elif xdev == rdf_file_finder.FileFinderArgs.XDev.NEVER:
    # Never cross device boundaries, stop at all mount points.
    return {os.stat(path).st_dev}

  elif xdev == rdf_file_finder.FileFinderArgs.XDev.LOCAL:
    # Descend into file systems on physical devices only.
    mount_points = _GetMountpoints(only_physical=True)
    res = {os.stat(path).st_dev}
    for mp in mount_points:
      try:
        res.add(os.stat(mp).st_dev)
      except OSError:
        pass
    return res

  else:
    raise ValueError("Incorrect `xdev` value: %s" % xdev)
