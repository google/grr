#!/usr/bin/env python
"""The file finder client action."""

from collections.abc import Callable, Iterator

from grr_response_client import actions
from grr_response_client import client_utils
from grr_response_client import vfs
from grr_response_client.client_actions.file_finder_utils import conditions
from grr_response_client.client_actions.file_finder_utils import globbing
from grr_response_client.client_actions.file_finder_utils import vfs_subactions
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.util import filesystem


def _NoOp():
  """Does nothing. This function is to be used as default heartbeat callback."""


class VfsFileFinder(actions.ActionPlugin):
  """The registry file finder implementation."""

  in_rdfvalue = rdf_file_finder.FileFinderArgs
  out_rdfvalues = [rdf_file_finder.FileFinderResult]

  def Run(self, args: rdf_file_finder.FileFinderArgs):
    action = self._ParseAction(args)
    content_conditions = list(
        conditions.ContentCondition.Parse(args.conditions)
    )
    metadata_conditions = list(
        conditions.MetadataCondition.Parse(args.conditions)
    )

    for path in _GetExpandedPaths(args, heartbeat_cb=self.Progress):
      self.Progress()
      pathspec = rdf_paths.PathSpec(path=path, pathtype=args.pathtype)
      if args.HasField("implementation_type"):
        pathspec.implementation_type = args.implementation_type

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
      self,
      args: rdf_file_finder.FileFinderArgs,
  ) -> vfs_subactions.Action:
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
    cur_matches = []
    with vfs.VFSOpen(pathspec) as vfs_file:
      is_registry = (
          vfs_file.supported_pathtype == rdf_paths.PathSpec.PathType.REGISTRY
      )
      # Do the actual matching for registry files or for files with a well
      # defined size.
      if is_registry or (vfs_file.size is not None and vfs_file.size > 0):
        cur_matches = list(cond.Search(vfs_file))

    if cur_matches:
      matches.extend(cur_matches)
    else:  # As soon as one condition does not match, we skip the file.
      return []  # Return no matches to indicate skipping this file.
  return matches


def _GetExpandedPaths(
    args: rdf_file_finder.FileFinderArgs,
    heartbeat_cb: Callable[[], None] = _NoOp,
) -> Iterator[str]:
  """Yields all possible expansions from given path patterns."""
  if args.HasField("implementation_type"):
    implementation_type = args.implementation_type
  else:
    implementation_type = None
  opts = globbing.PathOpts(
      follow_links=args.follow_links,
      pathtype=args.pathtype,
      implementation_type=implementation_type,
  )

  for path in args.paths:
    for expanded_path in globbing.ExpandPath(str(path), opts, heartbeat_cb):
      yield expanded_path
