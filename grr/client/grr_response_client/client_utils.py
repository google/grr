#!/usr/bin/env python
"""Client utilities."""

import logging
import os
import sys

from typing import Text

from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.util import filesystem

# pylint: disable=g-import-not-at-top
if sys.platform == "win32":
  from grr_response_client import client_utils_windows as _client_utils
elif sys.platform == "darwin":
  from grr_response_client import client_utils_osx as _client_utils
else:
  from grr_response_client import client_utils_linux as _client_utils
# pylint: enable=g-import-not-at-top

# pylint: disable=g-bad-name
CanonicalPathToLocalPath = _client_utils.CanonicalPathToLocalPath
FindProxies = _client_utils.FindProxies
GetExtAttrs = _client_utils.GetExtAttrs
GetRawDevice = _client_utils.GetRawDevice
KeepAlive = _client_utils.KeepAlive
LocalPathToCanonicalPath = _client_utils.LocalPathToCanonicalPath
MemoryRegions = _client_utils.MemoryRegions
OpenProcessForMemoryAccess = _client_utils.OpenProcessForMemoryAccess
TransactionLog = _client_utils.TransactionLog
VerifyFileOwner = _client_utils.VerifyFileOwner
CreateProcessFromSerializedFileDescriptor = _client_utils.CreateProcessFromSerializedFileDescriptor

# pylint: enable=g-bad-name


def StatEntryFromPath(
    path: Text,
    pathspec: rdf_paths.PathSpec,
    ext_attrs: bool = True,
    follow_symlink: bool = True,
) -> rdf_client_fs.StatEntry:
  """Builds a stat entry object from a given path.

  Args:
    path: A path (string value) to stat.
    pathspec: A `PathSpec` corresponding to the `path`.
    ext_attrs: Whether to include extended file attributes in the result.
    follow_symlink: Whether links should be followed.

  Returns:
    `StatEntry` object.
  """
  try:
    stat = filesystem.Stat.FromPath(path, follow_symlink=follow_symlink)
  except (IOError, OSError) as error:
    logging.error("Failed to obtain stat for '%s': %s", pathspec, error)
    return rdf_client_fs.StatEntry(pathspec=pathspec)

  return StatEntryFromStat(stat, pathspec, ext_attrs=ext_attrs)


def StatEntryFromStat(stat: filesystem.Stat,
                      pathspec: rdf_paths.PathSpec,
                      ext_attrs: bool = True) -> rdf_client_fs.StatEntry:
  """Build a stat entry object from a given stat object.

  Args:
    stat: A `Stat` object.
    pathspec: A `PathSpec` from which `stat` was obtained.
    ext_attrs: Whether to include extended file attributes in the result.

  Returns:
    `StatEntry` object.
  """
  result = rdf_client_fs.StatEntry(pathspec=pathspec)

  for attr in _STAT_ATTRS:
    value = getattr(stat.GetRaw(), attr, None)
    if value is None:
      continue

    # TODO(hanuszczak): Why are we doing this?
    value = int(value)
    if value < 0:
      value &= 0xFFFFFFFF

    setattr(result, attr, value)

  result.st_flags_linux = stat.GetLinuxFlags()
  result.st_flags_osx = stat.GetOsxFlags()
  if ext_attrs:
    # TODO(hanuszczak): Can we somehow incorporate extended attribute getter to
    # the `Stat` class? That would make the code a lot prettier but would force
    # `utils` to depend on `xattrs`.
    result.ext_attrs = list(GetExtAttrs(stat.GetPath()))

  if stat.GetSymlinkTarget() is not None:
    result.symlink = stat.GetSymlinkTarget()

  return result


def StatEntryFromStatPathSpec(stat: filesystem.Stat,
                              ext_attrs: bool) -> rdf_client_fs.StatEntry:
  pathspec = rdf_paths.PathSpec(
      pathtype=rdf_paths.PathSpec.PathType.OS,
      path=LocalPathToCanonicalPath(stat.GetPath()),
      path_options=rdf_paths.PathSpec.Options.CASE_LITERAL)
  return StatEntryFromStat(stat, pathspec, ext_attrs=ext_attrs)


def StatResultFromStatEntry(
    stat_entry: rdf_client_fs.StatEntry) -> os.stat_result:
  """Returns a `os.stat_result` with most information from `StatEntry`.

  This is a lossy conversion, only the 10 first stat_result fields are
  populated, because the os.stat_result constructor is inflexible.

  Args:
    stat_entry: An instance of rdf_client_fs.StatEntry.

  Returns:
    An instance of `os.stat_result` with basic fields populated.
  """
  values = []
  for attr in _STAT_ATTRS[:10]:
    values.append(stat_entry.Get(attr))
  return os.stat_result(values)


# It is important that the first 10 names are in the order that the stat_result
# constructor accepts. Only this way, a stat_result can be created from a
# StatEntry. See https://docs.python.org/3/library/os.html#os.stat_result
_STAT_ATTRS = [
    "st_mode",
    "st_ino",
    "st_dev",
    "st_nlink",
    "st_uid",
    "st_gid",
    "st_size",
    "st_atime",
    "st_mtime",
    "st_ctime",
    "st_blocks",
    "st_blksize",
    "st_rdev",
]
