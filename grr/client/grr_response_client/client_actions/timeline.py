#!/usr/bin/env python
"""A module with a client action for timeline collection."""
from __future__ import absolute_import
from __future__ import division

from __future__ import unicode_literals

import hashlib
import os
import stat as stat_mode

from typing import Iterator

from grr_response_client import actions
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.lib.rdfvalues import timeline as rdf_timeline


class Timeline(actions.ActionPlugin):
  """A client action for timeline collection."""

  in_rdfvalue = rdf_timeline.TimelineArgs
  out_rdfvalues = [rdf_timeline.TimelineResult]

  _TRANSFER_STORE_ID = rdfvalue.SessionID(flow_name="TransferStore")

  def Run(self, args):
    """Executes the client action."""
    result = rdf_timeline.TimelineResult()

    entries = Walk(args.root)
    for entry_batch in rdf_timeline.TimelineEntry.SerializeStream(entries):
      entry_batch_blob = rdf_protodict.DataBlob(data=entry_batch)
      self.SendReply(entry_batch_blob, session_id=self._TRANSFER_STORE_ID)

      entry_batch_blob_id = hashlib.sha256(entry_batch).digest()
      result.entry_batch_blob_ids.append(entry_batch_blob_id)

      self.Progress()

    self.SendReply(result)


def Walk(root):
  """Walks the filesystem collecting stat information.

  This method will recursively descend to all sub-folders and sub-sub-folders
  and so on. It will stop the recursion at device boundaries and will not follow
  any symlinks (to avoid cycles and virtual filesystems that may be potentially
  infinite).

  Args:
    root: A path to the root folder at which the recursion should start.

  Returns:
    An iterator over timeline entries with stat information about each file.
  """
  try:
    dev = os.lstat(root).st_dev
  except OSError:
    return iter([])

  def Recurse(path):
    """Performs the recursive walk over the file hierarchy."""
    try:
      stat = os.lstat(path)
    except OSError:
      return

    yield rdf_timeline.TimelineEntry.FromStat(path, stat)

    # We want to recurse only to folders on the same device.
    if not stat_mode.S_ISDIR(stat.st_mode) or stat.st_dev != dev:
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
