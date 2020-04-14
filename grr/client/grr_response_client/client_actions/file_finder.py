#!/usr/bin/env python
# Lint as: python3
"""The file finder client action."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import io

from typing import Callable, Iterator, Text, List

from grr_response_client import actions
from grr_response_client import client_utils
from grr_response_client.client_actions.file_finder_utils import conditions
from grr_response_client.client_actions.file_finder_utils import globbing
from grr_response_client.client_actions.file_finder_utils import subactions
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.util import filesystem


def _NoOp():
  """Does nothing. This function is to be used as default heartbeat callback."""


class _SkipFileException(Exception):
  pass


def FileFinderOSFromClient(args):
  """This function expands paths from the args and returns related stat entries.

  Args:
    args: An `rdf_file_finder.FileFinderArgs` object.

  Yields:
    `rdf_paths.PathSpec` instances.
  """
  stat_cache = filesystem.StatCache()

  opts = args.action.stat

  for path in GetExpandedPaths(args):
    try:
      content_conditions = conditions.ContentCondition.Parse(args.conditions)
      for content_condition in content_conditions:
        with io.open(path, "rb") as fd:
          result = list(content_condition.Search(fd))
        if not result:
          raise _SkipFileException()
      stat = stat_cache.Get(path, follow_symlink=opts.resolve_links)
      stat_entry = client_utils.StatEntryFromStatPathSpec(
          stat, ext_attrs=opts.collect_ext_attrs)
      yield stat_entry
    except _SkipFileException:
      pass


class FileFinderOS(actions.ActionPlugin):
  """The file finder implementation using the OS file api."""

  in_rdfvalue = rdf_file_finder.FileFinderArgs
  out_rdfvalues = [rdf_file_finder.FileFinderResult]

  def Run(self, args: rdf_file_finder.FileFinderArgs):
    if args.pathtype != rdf_paths.PathSpec.PathType.OS:
      raise ValueError(
          "FileFinderOS can only be used with OS paths, got {}".format(
              args.pathspec))

    self.stat_cache = filesystem.StatCache()

    action = self._ParseAction(args)
    self._metadata_conditions = list(
        conditions.MetadataCondition.Parse(args.conditions))
    self._content_conditions = list(
        conditions.ContentCondition.Parse(args.conditions))

    for path in GetExpandedPaths(args, heartbeat_cb=self.Progress):
      self.Progress()
      try:
        matches = self._Validate(args, path)
        result = rdf_file_finder.FileFinderResult()
        result.matches = matches
        action.Execute(path, result)
        self.SendReply(result)
      except _SkipFileException:
        pass

  def _ParseAction(self,
                   args: rdf_file_finder.FileFinderArgs) -> subactions.Action:
    action_type = args.action.action_type
    if action_type == rdf_file_finder.FileFinderAction.Action.STAT:
      return subactions.StatAction(self, args.action.stat)
    if action_type == rdf_file_finder.FileFinderAction.Action.HASH:
      return subactions.HashAction(self, args.action.hash)
    if action_type == rdf_file_finder.FileFinderAction.Action.DOWNLOAD:
      return subactions.DownloadAction(self, args.action.download)
    raise ValueError("Incorrect action type: %s" % action_type)

  def _GetStat(self, filepath, follow_symlink=True):
    try:
      return self.stat_cache.Get(filepath, follow_symlink=follow_symlink)
    except OSError:
      raise _SkipFileException()

  def _Validate(self, args: rdf_file_finder.FileFinderArgs,
                filepath: Text) -> List[rdf_client.BufferReference]:
    matches = []
    stat = self._GetStat(filepath, follow_symlink=bool(args.follow_links))
    self._ValidateRegularity(stat, args, filepath)
    self._ValidateMetadata(stat, filepath)
    self._ValidateContent(stat, filepath, matches)
    return matches

  def _ValidateRegularity(self, stat, args, filepath):
    if args.process_non_regular_files:
      return

    is_regular = stat.IsRegular() or stat.IsDirectory() or stat.IsSymlink()
    if not is_regular:
      raise _SkipFileException()

  def _ValidateMetadata(self, stat, filepath):
    for metadata_condition in self._metadata_conditions:
      if not metadata_condition.Check(stat):
        raise _SkipFileException()

  def _ValidateContent(self, stat, filepath, matches):
    if self._content_conditions and stat.IsDirectory():
      raise _SkipFileException()

    for content_condition in self._content_conditions:
      with io.open(filepath, "rb") as fd:
        result = list(content_condition.Search(fd))
      if not result:
        raise _SkipFileException()
      matches.extend(result)


def GetExpandedPaths(
    args: rdf_file_finder.FileFinderArgs,
    heartbeat_cb: Callable[[], None] = _NoOp) -> Iterator[Text]:
  """Expands given path patterns.

  Args:
    args: A `FileFinderArgs` instance that dictates the behaviour of the path
      expansion.
    heartbeat_cb: A function to be called regularly to send heartbeats.

  Yields:
    Absolute paths (as string objects) derived from input patterns.

  Raises:
    ValueError: For unsupported path types.
  """
  if args.pathtype == rdf_paths.PathSpec.PathType.OS:
    pathtype = rdf_paths.PathSpec.PathType.OS
  else:
    raise ValueError("Unsupported path type: ", args.pathtype)

  opts = globbing.PathOpts(
      follow_links=args.follow_links, xdev=args.xdev, pathtype=pathtype)

  for path in args.paths:
    for expanded_path in globbing.ExpandPath(str(path), opts, heartbeat_cb):
      yield expanded_path
