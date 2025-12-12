#!/usr/bin/env python
"""A module with a client action for timeline collection."""

from collections.abc import Iterator
import hashlib
import os
import stat as stat_mode
from typing import Optional

import psutil

from grr_response_client import actions
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import mig_timeline
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.lib.rdfvalues import timeline as rdf_timeline
from grr_response_core.lib.util import iterator
from grr_response_core.lib.util import statx


# Indicates whether the timeline action will also collect file birth time.
BTIME_SUPPORT: bool = statx.BTIME_SUPPORT


class Timeline(actions.ActionPlugin):
  """A client action for timeline collection."""

  in_rdfvalue = rdf_timeline.TimelineArgs
  out_rdfvalues = [rdf_timeline.TimelineResult]

  _TRANSFER_STORE_ID = rdfvalue.SessionID(flow_name="TransferStore")

  def Run(self, args: rdf_timeline.TimelineArgs) -> None:
    """Executes the client action."""
    fstype = GetFilesystemType(args.root)
    entries = iterator.Counted(Walk(args.root))
    proto_entries = (
        mig_timeline.ToProtoTimelineEntry(entry) for entry in entries
    )
    for entry_batch in rdf_timeline.SerializeTimelineEntryStream(proto_entries):
      entry_batch_blob = rdf_protodict.DataBlob(data=entry_batch)
      self.SendReply(entry_batch_blob, session_id=self._TRANSFER_STORE_ID)

      entry_batch_blob_id = hashlib.sha256(entry_batch).digest()

      result = rdf_timeline.TimelineResult()
      result.entry_batch_blob_ids.append(entry_batch_blob_id)
      result.entry_count = entries.count
      result.filesystem_type = fstype
      self.SendReply(result)

      # Each result should contain information only about the number of entries
      # in the current batch, so after the results are sent we simply reset the
      # counter.
      entries.Reset()


def Walk(root: bytes) -> Iterator[rdf_timeline.TimelineEntry]:
  """Walks the filesystem collecting stat information.

  This method will recursively descend to all sub-folders and sub-sub-folders
  and so on. It will stop the recursion at device boundaries and will not follow
  any symlinks (to avoid cycles and virtual filesystems that may be potentially
  infinite).

  Args:
    root: A path to the root folder at which the recursion should start.

  Returns:
    An iterator over timeline entries with stat information about each file.

  Raises:
    OSError: If it is not possible to collect information about the root folder.
    ValueError: If the specified root path is not absolute.
  """
  if not os.path.isabs(root):
    raise ValueError("Requested to traverse a non-root path")

  # We fully expand the root path in order for the timeline entries to have
  # the real path associated with them.
  root = os.path.realpath(root)

  # This might raise if there is a problem when accessing the path (e.g. it does
  # not exist). While for recursive walking we generally want to ignore such
  # errors (because given the multitude of files we are going to traverse there
  # are likely going to be permission errors for some of them), if we fail to
  # collect information about the root then likely something is wrong and the
  # flow should fail, giving the user a meaningful error message.
  dev = os.lstat(root).st_dev

  def Recurse(path: bytes) -> Iterator[rdf_timeline.TimelineEntry]:
    """Performs the recursive walk over the file hierarchy."""
    try:
      stat = statx.Get(path)
    except OSError:
      return

    yield rdf_timeline.TimelineEntry.FromStatx(path, stat)

    # We want to recurse only to folders on the same device.
    if not stat_mode.S_ISDIR(stat.mode) or stat.dev != dev:
      return

    try:
      childnames = os.listdir(path)
    except OSError:
      childnames = []

    # TODO(hanuszczak): Implement more efficient auto-batcher instead of having
    # multi-level iterators.
    for childname in childnames:
      for entry in Recurse(os.path.join(path, childname)):
        yield entry

  return Recurse(root)


def GetFilesystemType(root: bytes) -> Optional[str]:
  """Retrieves the type of a filesystem the given path belongs to.

  Note that the exact set of values that can be returned from this function is
  not specified and depends on how the operating system represents filesystem
  names. For example, an NTFS filesystem can be represented by uppercase `NTFS`
  string on Windows but lowercase `ntfs` string on Linux.

  Args:
    root: A path to check the filesystem for.

  Returns:
    A string representing the type of the filesystem or `None` if the filesystem
    type could not be determined.
  """
  # While we want to ignore errors when stating individual partitions (since we
  # might lack permission to do so in some cases), we don't do it for the root
  # path itself as root path has to be accessible for the action to provide any
  # meaningful result. If it is not, we want to fail loudly so that the flow is
  # notified about the problem.
  root_dev = os.lstat(root).st_dev

  for part in psutil.disk_partitions():
    try:
      part_dev = os.lstat(part.mountpoint).st_dev
    except IOError:
      continue

    if root_dev == part_dev:
      return part.fstype

  return None
