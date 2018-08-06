#!/usr/bin/env python
"""The MySQL database methods for path handling."""


class MySQLDBPathMixin(object):
  """MySQLDB mixin for path related functions."""

  def ReadPathInfo(self, client_id, path_type, components, timestamp=None):
    """Retrieves a path info record for a given path."""
    raise NotImplementedError()

  def ReadPathInfos(self, client_id, path_type, components_list):
    """Retrieves path info records for given paths."""
    raise NotImplementedError()

  def WritePathInfos(self, client_id, path_infos):
    """Writes a collection of path_info records for a client."""
    raise NotImplementedError()

  def InitPathInfos(self, client_id, path_infos):
    """Initializes a collection of path info records for a client."""
    raise NotImplementedError()

  def ListDescendentPathInfos(self,
                              client_id,
                              path_type,
                              components,
                              max_depth=None):
    """Lists path info records that correspond to descendants of given path."""
    raise NotImplementedError()

  def MultiWritePathHistory(self, client_id, stat_entries, hash_entries):
    raise NotImplementedError()

  def ReadPathInfosHistories(self, client_id, path_type, components_list):
    """Reads a collection of hash and stat entries for given paths."""

    raise NotImplementedError()
