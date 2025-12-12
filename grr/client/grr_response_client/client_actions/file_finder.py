#!/usr/bin/env python
"""The file finder client action."""

from collections.abc import Callable, Iterator
import io
import logging

from grr_response_client import actions
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


class FileFinderOS(actions.ActionPlugin):
  """The file finder implementation using the OS file api."""

  in_rdfvalue = rdf_file_finder.FileFinderArgs
  out_rdfvalues = [rdf_file_finder.FileFinderResult]

  def Run(self, args: rdf_file_finder.FileFinderArgs):
    if args.pathtype != rdf_paths.PathSpec.PathType.OS:
      raise ValueError(
          "FileFinderOS can only be used with OS paths, got {}".format(
              args.pathspec
          )
      )

    self.stat_cache = filesystem.StatCache()

    action = self._ParseAction(args)
    self._metadata_conditions = list(
        conditions.MetadataCondition.Parse(args.conditions)
    )
    self._content_conditions = list(
        conditions.ContentCondition.Parse(args.conditions)
    )

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

  def _ParseAction(
      self, args: rdf_file_finder.FileFinderArgs
  ) -> subactions.Action:
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
    except OSError as e:
      logging.info("Failed to stat '%s': %s", filepath, e)
      raise _SkipFileException() from e

  def _Validate(
      self, args: rdf_file_finder.FileFinderArgs, filepath: str
  ) -> list[rdf_client.BufferReference]:
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
    # This check ensures consistent behavior between the legacy file finder and
    # the client file finder. The legacy file finder was automatically
    # following symlinks to regular files.
    if stat.IsSymlink():
      link_path = stat.GetPath()
      try:
        target_stat = filesystem.Stat.FromPath(link_path, follow_symlink=True)
      except FileNotFoundError:
        logging.info("Broken link '%s'", link_path)
      else:
        if target_stat.IsRegular():
          stat = target_stat

    for metadata_condition in self._metadata_conditions:
      if not metadata_condition.Check(stat):
        raise _SkipFileException()

  def _ValidateContent(self, stat, filepath, matches):
    if self._content_conditions and not stat.IsRegular():
      # This check ensures consistent behavior between the legacy file finder
      # and the client file finder. The legacy file finder was automatically
      # following symlinks to regular files.
      if stat.IsSymlink():
        link_path = stat.GetPath()
        try:
          target_stat = filesystem.Stat.FromPath(link_path, follow_symlink=True)
        except FileNotFoundError:
          logging.info("Broken link '%s'", link_path)
        else:
          if not target_stat.IsRegular():
            raise _SkipFileException()
      else:
        raise _SkipFileException()

    for content_condition in self._content_conditions:
      try:
        with io.open(filepath, "rb") as fd:
          result = list(content_condition.Search(fd))
      except OSError as e:
        logging.error("Error reading '%s': %s", filepath, e)
        raise _SkipFileException() from e
      if not result:
        raise _SkipFileException()
      matches.extend(result)


def GetExpandedPaths(
    args: rdf_file_finder.FileFinderArgs,
    heartbeat_cb: Callable[[], None] = _NoOp,
) -> Iterator[str]:
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
      follow_links=args.follow_links, xdev=args.xdev, pathtype=pathtype
  )

  for path in args.paths:
    for expanded_path in globbing.ExpandPath(str(path), opts, heartbeat_cb):
      yield expanded_path
