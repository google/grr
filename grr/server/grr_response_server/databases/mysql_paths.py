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

  def MultiWritePathInfos(self, path_infos):
    """Writes a collection of path info records for specified clients."""
    raise NotImplementedError()

  def ClearPathHistory(self, client_id, path_infos):
    """Clears path history for specified paths of given client."""
    raise NotImplementedError()

  def MultiClearPathHistory(self, path_infos):
    """Clears path history for specified paths of given clients."""
    raise NotImplementedError()

  def ListDescendentPathInfos(self,
                              client_id,
                              path_type,
                              components,
                              max_depth=None):
    """Lists path info records that correspond to descendants of given path."""
    raise NotImplementedError()

  def MultiWritePathHistory(self, client_path_histories):
    raise NotImplementedError()

  def ReadPathInfosHistories(self, client_id, path_type, components_list):
    """Reads a collection of hash and stat entries for given paths."""
    raise NotImplementedError()

  def ReadLatestPathInfosWithHashBlobReferences(self,
                                                client_paths,
                                                max_timestamp=None):
    """Returns PathInfos that have corresponding HashBlobReferences."""
    raise NotImplementedError()
