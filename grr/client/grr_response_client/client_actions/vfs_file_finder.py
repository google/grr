#!/usr/bin/env python
"""The file finder client action."""
from __future__ import absolute_import
from __future__ import division

from __future__ import unicode_literals

from future.builtins import str
from typing import Text, Iterator

from grr_response_client import actions
from grr_response_client import client_utils
from grr_response_client import vfs
from grr_response_client.client_actions.file_finder_utils import conditions
from grr_response_client.client_actions.file_finder_utils import globbing
from grr_response_client.client_actions.file_finder_utils import vfs_subactions
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.util import filesystem


class VfsFileFinder(actions.ActionPlugin):
  """The registry file finder implementation."""

  in_rdfvalue = rdf_file_finder.FileFinderArgs
  out_rdfvalues = [rdf_file_finder.FileFinderResult]

  def Run(self, args):
    action = self._ParseAction(args)
    content_conditions = list(
        conditions.ContentCondition.Parse(args.conditions))
    metadata_conditions = list(
        conditions.MetadataCondition.Parse(args.conditions))

    for path in _GetExpandedPaths(args):
      self.Progress()
      pathspec = rdf_paths.PathSpec(path=path, pathtype=args.pathtype)

      with vfs.VFSOpen(pathspec) as vfs_file:
        stat_entry = vfs_file.Stat()

      # Conversion from StatEntry to os.stat_result is lossy. Some checks do
      # not work (e.g. extended attributes).
      stat_obj = client_utils.StatResultFromStatEntry(stat_entry)
      fs_stat = filesystem.Stat(path=path, stat_obj=stat_obj)
      if not all(cond.Check(fs_stat) for cond in metadata_conditions):
        continue

      matches = _CheckConditionsShortCircuit(content_conditions, pathspec)
      if content_conditions and not matches:
        continue  # Skip if any condition yielded no matches.

      result = action(stat_entry=stat_entry, fd=vfs_file)
      result.matches = matches
      self.SendReply(result)

  def _ParseAction(
      self, args):
    action_type = args.action.action_type
    if action_type == rdf_file_finder.FileFinderAction.Action.HASH:
      return vfs_subactions.HashAction(self, args.action.hash)
    if action_type == rdf_file_finder.FileFinderAction.Action.DOWNLOAD:
      return vfs_subactions.DownloadAction(self, args.action.download)
    else:
      return vfs_subactions.StatAction(self, args.action.stat)


def _CheckConditionsShortCircuit(content_conditions, pathspec):
  """Checks all `content_conditions` until one yields no matches."""
  matches = []
  for cond in content_conditions:
    with vfs.VFSOpen(pathspec) as vfs_file:
      cur_matches = list(cond.Search(vfs_file))
    if cur_matches:
      matches.extend(cur_matches)
    else:  # As soon as one condition does not match, we skip the file.
      return []  # Return no matches to indicate skipping this file.
  return matches


def _GetExpandedPaths(args):
  """Yields all possible expansions from given path patterns."""
  opts = globbing.PathOpts(
      follow_links=args.follow_links, pathtype=args.pathtype)

  for path in args.paths:
    for expanded_path in globbing.ExpandPath(str(path), opts):
      yield expanded_path


# TODO: This is only used by artifact_collector. It should be
# removed and artifact_collector should use VfsFileFinder or VFS directly.
def RegistryKeyFromClient(args):
  """This function expands paths from the args and returns registry keys.

  Args:
    args: An `rdf_file_finder.FileFinderArgs` object.

  Yields:
    `rdf_client_fs.StatEntry` instances.
  """
  for path in _GetExpandedPaths(args):
    pathspec = rdf_paths.PathSpec(
        path=path, pathtype=rdf_paths.PathSpec.PathType.REGISTRY)
    with vfs.VFSOpen(pathspec) as file_obj:
      yield file_obj.Stat()
