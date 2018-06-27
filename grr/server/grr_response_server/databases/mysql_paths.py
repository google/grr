#!/usr/bin/env python
"""The MySQL database methods for path handling."""


class MySQLDBPathMixin(object):
  """MySQLDB mixin for path related functions."""

  def FindPathInfoByPathID(self, client_id, path_type, path_ids,
                           timestamp=None):
    raise NotImplementedError()

  def FindPathInfosByPathIDs(self, client_id, path_type, path_ids):
    """Returns path info records for a client."""
    raise NotImplementedError()

  def WritePathInfos(self, client_id, path_infos):
    """Writes a collection of path_info records for a client."""
    raise NotImplementedError()

  def FindDescendentPathIDs(self, client_id, path_id, max_depth=None):
    """Finds all path_ids seen on a client descent from path_id."""
    raise NotImplementedError()
