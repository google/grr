#!/usr/bin/env python
"""The in memory database methods for path handling."""

from grr.lib import rdfvalue
from grr.lib import utils
from grr.server.grr_response_server import db
from grr.server.grr_response_server.rdfvalues import objects


class _PathRecord(object):
  """A class representing all known information about particular path.

  Attributes:
    path_type: A path type of the path that this record corresponds to.
    components: A path components of the path that this record corresponds to.
  """

  def __init__(self, path_type, components):
    self._path_info = objects.PathInfo(
        path_type=path_type, components=components)

    self._stat_entries = {}
    self._hash_entries = {}
    self._children = set()

  def AddPathHistory(self, path_info):
    """Extends the path record history and updates existing information."""
    self.AddPathInfo(path_info)

    timestamp = rdfvalue.RDFDatetime.Now()
    if path_info.HasField("stat_entry"):
      self._stat_entries[timestamp] = path_info.stat_entry.Copy()
    if path_info.HasField("hash_entry"):
      self._hash_entries[timestamp] = path_info.hash_entry.Copy()

  def AddPathInfo(self, path_info):
    """Updates existing path information of the path record."""
    if self._path_info.path_type != path_info.path_type:
      message = "Incompatible path types: `%s` and `%s`"
      raise ValueError(
          message % (self._path_info.path_type, path_info.path_type))
    if self._path_info.components != path_info.components:
      message = "Incompatible path components: `%s` and `%s`"
      raise ValueError(
          message % (self._path_info.components, path_info.components))

    self._path_info.timestamp = rdfvalue.RDFDatetime.Now()
    self._path_info.directory |= path_info.directory

  def AddChild(self, path_info):
    """Makes the path aware of some child."""
    if self._path_info.path_type != path_info.path_type:
      message = "Incompatible path types: `%s` and `%s`"
      raise ValueError(
          message % (self._path_info.path_type, path_info.path_type))
    if self._path_info.components != path_info.components[:-1]:
      message = "Incompatible path components, expected `%s` but got `%s`"
      raise ValueError(
          message % (self._path_info.components, path_info.components[:-1]))

    self._children.add(path_info.GetPathID())

  def GetPathInfo(self, timestamp=None):
    """Generates a summary about the path record.

    Args:
      timestamp: A point in time from which the data should be retrieved.

    Returns:
      A `rdf_objects.PathInfo` instance.
    """
    result = self._path_info.Copy()

    stat_entry_timestamp = self._LastEntryTimestamp(self._stat_entries,
                                                    timestamp)
    result.last_stat_entry_timestamp = stat_entry_timestamp
    result.stat_entry = self._stat_entries.get(stat_entry_timestamp)

    hash_entry_timestamp = self._LastEntryTimestamp(self._hash_entries,
                                                    timestamp)
    result.last_hash_entry_timestamp = hash_entry_timestamp
    result.hash_entry = self._hash_entries.get(hash_entry_timestamp)

    return result

  def GetChildren(self):
    return set(self._children)

  @staticmethod
  def _LastEntryTimestamp(collection, upper_bound_timestamp):
    """Searches for greatest timestamp lower than the specified one.

    Args:
      collection: A dictionary from timestamps to some items.
      upper_bound_timestamp: An upper bound for timestamp to be returned.

    Returns:
      Greatest timestamp that is lower than the specified one. If no such value
      exists, `None` is returned.
    """
    if upper_bound_timestamp is None:
      upper_bound_timestamp = rdfvalue.RDFDatetime.Now()

    upper_bound = lambda key: key <= upper_bound_timestamp

    try:
      return max(filter(upper_bound, collection.keys()))
    except ValueError:  # Thrown if `max` input (result of filtering) is empty.
      return None


class InMemoryDBPathMixin(object):
  """InMemoryDB mixin for path related functions."""

  @utils.Synchronized
  def FindPathInfoByPathID(self, client_id, path_type, path_id, timestamp=None):
    try:
      path_record = self.path_records[(client_id, path_type, path_id)]
      return path_record.GetPathInfo(timestamp=timestamp)
    except KeyError:
      raise db.UnknownPathError(
          client_id=client_id, path_type=path_type, path_id=path_id)

  @utils.Synchronized
  def FindPathInfosByPathIDs(self, client_id, path_type, path_ids):
    """Returns path info records for a client."""
    ret = {}
    for path_id in path_ids:
      try:
        path_record = self.path_records[(client_id, path_type, path_id)]
        ret[path_id] = path_record.GetPathInfo()
      except KeyError:
        ret[path_id] = None
    return ret

  def _GetPathRecord(self, client_id, path_info):
    path_idx = (client_id, path_info.path_type, path_info.GetPathID())
    return self.path_records.setdefault(
        path_idx,
        _PathRecord(
            path_type=path_info.path_type, components=path_info.components))

  def _WritePathInfo(self, client_id, path_info, ancestor):
    """Writes a single path info record for given client."""
    if client_id not in self.metadatas:
      raise db.UnknownClientError(client_id)

    path_record = self._GetPathRecord(client_id, path_info)
    if not ancestor:
      path_record.AddPathHistory(path_info)
    else:
      path_record.AddPathInfo(path_info)

    parent_path_info = path_info.GetParent()
    if parent_path_info is not None:
      parent_path_record = self._GetPathRecord(client_id, parent_path_info)
      parent_path_record.AddChild(path_info)

  @utils.Synchronized
  def WritePathInfos(self, client_id, path_infos):
    for path_info in path_infos:
      self._WritePathInfo(client_id, path_info, ancestor=False)
      for ancestor_path_info in path_info.GetAncestors():
        self._WritePathInfo(client_id, ancestor_path_info, ancestor=True)

  @utils.Synchronized
  def FindDescendentPathIDs(self, client_id, path_type, path_id,
                            max_depth=None):
    """Finds all path_ids seen on a client descent from path_id."""
    descendents = set()
    if max_depth == 0:
      return descendents

    next_depth = None
    if max_depth is not None:
      next_depth = max_depth - 1

    path_record = self.path_records[(client_id, path_type, path_id)]
    for child_path_id in path_record.GetChildren():
      descendents.add(child_path_id)
      descendents.update(
          self.FindDescendentPathIDs(
              client_id, path_type, child_path_id, max_depth=next_depth))

    return descendents
