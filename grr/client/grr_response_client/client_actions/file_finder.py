#!/usr/bin/env python
"""The file finder client action."""

import psutil

from grr_response_client import actions
from grr_response_client.client_actions.file_finder_utils import conditions
from grr_response_client.client_actions.file_finder_utils import globbing
from grr_response_client.client_actions.file_finder_utils import subactions
from grr.lib import utils
from grr.lib.rdfvalues import file_finder as rdf_file_finder


class _SkipFileException(Exception):
  pass


class FileFinderOS(actions.ActionPlugin):
  """The file finder implementation using the OS file api."""

  in_rdfvalue = rdf_file_finder.FileFinderArgs
  out_rdfvalues = [rdf_file_finder.FileFinderResult]

  def Run(self, args):
    self.stat_cache = utils.StatCache()

    action = self._ParseAction(args)
    for path in self._GetExpandedPaths(args):
      self.Progress()
      try:
        matches = self._Validate(args, path)
        result = rdf_file_finder.FileFinderResult()
        result.matches = matches
        action.Execute(path, result)
        self.SendReply(result)
      except _SkipFileException:
        pass

  def _ParseAction(self, args):
    action_type = args.action.action_type
    if action_type == rdf_file_finder.FileFinderAction.Action.STAT:
      return subactions.StatAction(self, args.action.stat)
    if action_type == rdf_file_finder.FileFinderAction.Action.HASH:
      return subactions.HashAction(self, args.action.hash)
    if action_type == rdf_file_finder.FileFinderAction.Action.DOWNLOAD:
      return subactions.DownloadAction(self, args.action.download)
    raise ValueError("Incorrect action type: %s" % action_type)

  def _GetExpandedPaths(self, args):
    """Expands given path patterns.

    Args:
      args: A `FileFinderArgs` instance that dictates the behaviour of the path
          expansion.

    Yields:
      Absolute paths (as string objects) derived from input patterns.
    """
    opts = globbing.PathOpts(
        follow_links=args.follow_links,
        recursion_blacklist=_GetMountpointBlacklist(args.xdev))

    for path in args.paths:
      for expanded_path in globbing.ExpandPath(utils.SmartStr(path), opts):
        yield expanded_path

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

    for metadata_condition in _ParseMetadataConditions(args):
      if not metadata_condition.Check(stat):
        raise _SkipFileException()

  def _ValidateContent(self, args, filepath, matches):
    for content_condition in _ParseContentConditions(args):
      result = list(content_condition.Search(filepath))
      if not result:
        raise _SkipFileException()
      matches.extend(result)


def _ParseMetadataConditions(args):
  return conditions.MetadataCondition.Parse(args.conditions)


def _ParseContentConditions(args):
  return conditions.ContentCondition.Parse(args.conditions)


def _GetMountpoints(only_physical=True):
  """Fetches a list of mountpoints.

  Args:
    only_physical: Determines whether only mountpoints for physical devices
        (e.g. hard disks) should be listed. If false, mountpoints for things
        such as memory partitions or `/dev/shm` will be returned as well.

  Returns:
    A set of mountpoints.
  """
  partitions = psutil.disk_partitions(all=not only_physical)
  return set(partition.mountpoint for partition in partitions)


def _GetMountpointBlacklist(xdev):
  """Builds a list of mountpoints to ignore during recursive searches.

  Args:
    xdev: A `XDev` value that determines policy for crossing device boundaries.

  Returns:
    A set of mountpoints to ignore.

  Raises:
    ValueError: If `xdev` value is invalid.
  """
  if xdev == rdf_file_finder.FileFinderArgs.XDev.NEVER:
    # Never cross device boundaries, stop at all mount points.
    return _GetMountpoints(only_physical=False)

  if xdev == rdf_file_finder.FileFinderArgs.XDev.LOCAL:
    # Descend into file systems on physical devices only.
    physical = _GetMountpoints(only_physical=True)
    return _GetMountpoints(only_physical=False) - physical

  if xdev == rdf_file_finder.FileFinderArgs.XDev.ALWAYS:
    # Never stop at any device boundary.
    return set()

  raise ValueError("Incorrect `xdev` value: %s" % xdev)
