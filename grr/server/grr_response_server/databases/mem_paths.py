#!/usr/bin/env python
"""The in memory database methods for path handling."""
from __future__ import unicode_literals


from builtins import filter  # pylint: disable=redefined-builtin
from future.utils import iteritems
from future.utils import iterkeys
from future.utils import itervalues

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_server import db
from grr_response_server.rdfvalues import objects as rdf_objects


class _PathRecord(object):
  """A class representing all known information about particular path.

  Attributes:
    path_type: A path type of the path that this record corresponds to.
    components: A path components of the path that this record corresponds to.
  """

  def __init__(self, path_type, components):
    self._path_info = rdf_objects.PathInfo(
        path_type=path_type, components=components)

    self._stat_entries = {}
    self._hash_entries = {}
    self._blob_references = {}
    self._children = set()

  def AddBlobReference(self, blob_ref):
    self._blob_references[blob_ref.offset] = blob_ref.Copy()

  def AddStatEntry(self, stat_entry, timestamp):
    if timestamp in self._stat_entries:
      message = ("Duplicated stat entry write for path '%s' of type '%s' at "
                 "timestamp '%s'. Old: %s. New: %s.")
      message %= ("/".join(self._path_info.components),
                  self._path_info.path_type, timestamp,
                  self._stat_entries[timestamp], stat_entry)
      raise db.Error(message)

    self._stat_entries[timestamp] = stat_entry.Copy()

  def GetStatEntries(self):
    return self._stat_entries.items()

  def AddHashEntry(self, hash_entry, timestamp):
    if timestamp in self._hash_entries:
      message = ("Duplicated hash entry write for path '%s' of type '%s' at "
                 "timestamp '%s'. Old: %s. New: %s.")
      message %= ("/".join(self._path_info.components),
                  self._path_info.path_type, timestamp,
                  self._hash_entries[timestamp], hash_entry)
      raise db.Error(message)

    self._hash_entries[timestamp] = hash_entry.Copy()

  def GetHashEntries(self):
    return self._hash_entries.items()

  def AddPathHistory(self, path_info):
    """Extends the path record history and updates existing information."""
    self.AddPathInfo(path_info)

    timestamp = rdfvalue.RDFDatetime.Now()
    if path_info.HasField("stat_entry"):
      self.AddStatEntry(path_info.stat_entry, timestamp)
    if path_info.HasField("hash_entry"):
      self.AddHashEntry(path_info.hash_entry, timestamp)

  def ClearHistory(self):
    self._stat_entries = {}
    self._hash_entries = {}

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

  def GetBlobReferences(self):
    return itervalues(self._blob_references)

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
      return max(filter(upper_bound, iterkeys(collection)))
    except ValueError:  # Thrown if `max` input (result of filtering) is empty.
      return None


class InMemoryDBPathMixin(object):
  """InMemoryDB mixin for path related functions."""

  @utils.Synchronized
  def ReadPathInfo(self, client_id, path_type, components, timestamp=None):
    """Retrieves a path info record for a given path."""
    try:
      path_record = self.path_records[(client_id, path_type, components)]
      return path_record.GetPathInfo(timestamp=timestamp)
    except KeyError:
      raise db.UnknownPathError(
          client_id=client_id, path_type=path_type, components=components)

  @utils.Synchronized
  def ReadPathInfos(self, client_id, path_type, components_list):
    """Retrieves path info records for given paths."""
    result = {}

    for components in components_list:
      try:
        path_record = self.path_records[(client_id, path_type, components)]
        result[components] = path_record.GetPathInfo()
      except KeyError:
        result[components] = None

    return result

  @utils.Synchronized
  def ListDescendentPathInfos(self,
                              client_id,
                              path_type,
                              components,
                              max_depth=None):
    """Lists path info records that correspond to children of given path."""
    result = []

    for path_idx, path_record in iteritems(self.path_records):
      other_client_id, other_path_type, other_components = path_idx
      if client_id != other_client_id or path_type != other_path_type:
        continue
      if len(other_components) == len(components):
        continue
      if not utils.IterableStartsWith(other_components, components):
        continue
      if (max_depth is not None and
          len(other_components) - len(components) > max_depth):
        continue

      result.append(path_record.GetPathInfo())

    result.sort(key=lambda _: tuple(_.components))
    return result

  def _GetPathRecord(self, client_id, path_info, set_default=True):
    components = tuple(path_info.components)
    path_idx = (client_id, path_info.path_type, components)

    if set_default:
      default = _PathRecord(
          path_type=path_info.path_type, components=components)
      return self.path_records.setdefault(path_idx, default)
    else:
      return self.path_records.get(path_idx, None)

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
  def MultiWritePathInfos(self, path_infos):
    for client_id, client_path_infos in iteritems(path_infos):
      self.WritePathInfos(client_id, client_path_infos)

  @utils.Synchronized
  def WritePathInfos(self, client_id, path_infos):
    for path_info in path_infos:
      self._WritePathInfo(client_id, path_info, ancestor=False)
      for ancestor_path_info in path_info.GetAncestors():
        self._WritePathInfo(client_id, ancestor_path_info, ancestor=True)

  @utils.Synchronized
  def MultiClearPathHistory(self, path_infos):
    """Clears path history for specified paths of given clients."""
    for client_id, client_path_infos in iteritems(path_infos):
      self.ClearPathHistory(client_id, client_path_infos)

  @utils.Synchronized
  def ClearPathHistory(self, client_id, path_infos):
    """Clears path history for specified paths of given client."""
    for path_info in path_infos:
      path_record = self._GetPathRecord(client_id, path_info)
      path_record.ClearHistory()

  @utils.Synchronized
  def MultiWritePathHistory(self, client_path_histories):
    """Writes a collection of hash and stat entries observed for given paths."""
    for client_path, client_path_history in iteritems(client_path_histories):
      if client_path.client_id not in self.metadatas:
        raise db.UnknownClientError(client_path.client_id)

      path_info = rdf_objects.PathInfo(
          path_type=client_path.path_type, components=client_path.components)

      for timestamp, stat_entry in iteritems(client_path_history.stat_entries):
        path_record = self._GetPathRecord(
            client_path.client_id, path_info, set_default=False)
        if path_record is None:
          # TODO(hanuszczak): Provide more details about paths that caused that.
          raise db.AtLeastOneUnknownPathError([])

        path_record.AddStatEntry(stat_entry, timestamp)

      for timestamp, hash_entry in iteritems(client_path_history.hash_entries):
        path_record = self._GetPathRecord(
            client_path.client_id, path_info, set_default=False)
        if path_record is None:
          # TODO(hanuszczak): Provide more details about paths that caused that.
          raise db.AtLeastOneUnknownPathError([])

        path_record.AddHashEntry(hash_entry, timestamp)

  @utils.Synchronized
  def ReadPathInfosHistories(self, client_id, path_type, components_list):
    """Reads a collection of hash and stat entries for given paths."""
    results = {}

    for components in components_list:
      try:
        path_record = self.path_records[(client_id, path_type, components)]
      except KeyError:
        results[components] = []
        continue

      entries_by_ts = {}
      for ts, stat_entry in path_record.GetStatEntries():
        pi = rdf_objects.PathInfo(
            path_type=path_type,
            components=components,
            timestamp=ts,
            stat_entry=stat_entry)
        entries_by_ts[ts] = pi

      for ts, hash_entry in path_record.GetHashEntries():
        try:
          pi = entries_by_ts[ts]
        except KeyError:
          pi = rdf_objects.PathInfo(
              path_type=path_type, components=components, timestamp=ts)
          entries_by_ts[ts] = pi

        pi.hash_entry = hash_entry

      results[components] = [
          entries_by_ts[k] for k in sorted(iterkeys(entries_by_ts))
      ]

    return results
