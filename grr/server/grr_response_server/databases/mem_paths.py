#!/usr/bin/env python
"""The in memory database methods for path handling."""

from typing import Dict
from typing import Iterable
from typing import Optional
from typing import Sequence
from typing import Text

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.util import collection
from grr_response_server.databases import db
from grr_response_server.rdfvalues import objects as rdf_objects


class _PathRecord(object):
  """A class representing all known information about particular path.

  Attributes:
    path_type: A path type of the path that this record corresponds to.
    components: A path components of the path that this record corresponds to.
  """

  def __init__(self, path_type, components):
    self._path_type = path_type
    self._components = components

    self._path_infos = {}
    self._children = set()

  @property
  def _stat_entries(self):
    return {
        ts: pi.stat_entry
        for ts, pi in self._path_infos.items()
        if pi.stat_entry
    }

  @property
  def _hash_entries(self):
    return {
        ts: pi.hash_entry
        for ts, pi in self._path_infos.items()
        if pi.hash_entry
    }

  def AddStatEntry(self, stat_entry, timestamp):
    """Registers stat entry at a given timestamp."""

    if timestamp in self._stat_entries:
      message = ("Duplicated stat entry write for path '%s' of type '%s' at "
                 "timestamp '%s'. Old: %s. New: %s.")
      message %= ("/".join(self._components), self._path_type, timestamp,
                  self._stat_entries[timestamp], stat_entry)
      raise db.Error(message)

    if timestamp not in self._path_infos:
      path_info = rdf_objects.PathInfo(
          path_type=self._path_type,
          components=self._components,
          timestamp=timestamp,
          stat_entry=stat_entry)
      self.AddPathInfo(path_info)
    else:
      self._path_infos[timestamp].stat_entry = stat_entry

  def GetStatEntries(self):
    return self._stat_entries.items()

  def AddHashEntry(self, hash_entry, timestamp):
    """Registers hash entry at a given timestamp."""

    if timestamp in self._hash_entries:
      message = ("Duplicated hash entry write for path '%s' of type '%s' at "
                 "timestamp '%s'. Old: %s. New: %s.")
      message %= ("/".join(self._components), self._path_type, timestamp,
                  self._hash_entries[timestamp], hash_entry)
      raise db.Error(message)

    if timestamp not in self._path_infos:
      path_info = rdf_objects.PathInfo(
          path_type=self._path_type,
          components=self._components,
          timestamp=timestamp,
          hash_entry=hash_entry)
      self.AddPathInfo(path_info)
    else:
      self._path_infos[timestamp].hash_entry = hash_entry

  def GetHashEntries(self):
    return self._hash_entries.items()

  def ClearHistory(self):
    self._path_infos = {}

  def AddPathInfo(self, path_info):
    """Updates existing path information of the path record."""

    if self._path_type != path_info.path_type:
      message = "Incompatible path types: `%s` and `%s`"
      raise ValueError(message % (self._path_type, path_info.path_type))
    if self._components != path_info.components:
      message = "Incompatible path components: `%s` and `%s`"
      raise ValueError(message % (self._components, path_info.components))

    if path_info.timestamp in self._path_infos:
      raise ValueError("PathInfo with timestamp %r was added before." %
                       path_info.timestamp)

    new_path_info = path_info.Copy()
    if new_path_info.timestamp is None:
      new_path_info.timestamp = rdfvalue.RDFDatetime.Now()
    self._path_infos[new_path_info.timestamp] = new_path_info

  def AddChild(self, path_info):
    """Makes the path aware of some child."""

    if self._path_type != path_info.path_type:
      message = "Incompatible path types: `%s` and `%s`"
      raise ValueError(message % (self._path_type, path_info.path_type))
    if self._components != path_info.components[:-1]:
      message = "Incompatible path components, expected `%s` but got `%s`"
      raise ValueError(message % (self._components, path_info.components[:-1]))

    self._children.add(path_info.GetPathID())

  def GetPathInfo(self, timestamp=None):
    """Generates a summary about the path record.

    Args:
      timestamp: A point in time from which the data should be retrieved.

    Returns:
      A `rdf_objects.PathInfo` instance.
    """
    path_info_timestamp = self._LastEntryTimestamp(self._path_infos, timestamp)
    try:
      result = self._path_infos[path_info_timestamp].Copy()
    except KeyError:
      result = rdf_objects.PathInfo(
          path_type=self._path_type,
          components=self._components,
          directory=True)

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
  def _LastEntryTimestamp(dct, upper_bound_timestamp):
    """Searches for greatest timestamp lower than the specified one.

    Args:
      dct: A dictionary from timestamps to some items.
      upper_bound_timestamp: An upper bound for timestamp to be returned.

    Returns:
      Greatest timestamp that is lower than the specified one. If no such value
      exists, `None` is returned.
    """
    if upper_bound_timestamp is None:
      upper_bound = lambda _: True
    else:
      upper_bound = lambda key: key <= upper_bound_timestamp

    try:
      return max(filter(upper_bound, dct.keys()))
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
  def ListDescendantPathInfos(self,
                              client_id,
                              path_type,
                              components,
                              timestamp=None,
                              max_depth=None):
    """Lists path info records that correspond to children of given path."""
    result = []
    root_dir_exists = False

    for path_idx, path_record in self.path_records.items():
      other_client_id, other_path_type, other_components = path_idx
      path_info = path_record.GetPathInfo(timestamp=timestamp)

      if client_id != other_client_id or path_type != other_path_type:
        continue
      if other_components == tuple(components):
        root_dir_exists = True
        if not path_info.directory:
          raise db.NotDirectoryPathError(client_id, path_type, components)
      if len(other_components) == len(components):
        continue
      if not collection.StartsWith(other_components, components):
        continue
      if (max_depth is not None and
          len(other_components) - len(components) > max_depth):
        continue

      result.append(path_info)

    if not root_dir_exists and components:
      raise db.UnknownPathError(client_id, path_type, components)

    if timestamp is None:
      return sorted(result, key=lambda _: tuple(_.components))

    # We need to filter implicit path infos if specific timestamp is given.

    # TODO(hanuszczak): If we were to switch to use path trie instead of storing
    # records by path id, everything would be much easier.

    class TrieNode(object):
      """A trie of path components with path infos as values."""

      def __init__(self):
        self.path_info = None
        self.children = {}
        self.explicit = False

      def Add(self, path_info, idx=0):
        """Adds given path info to the trie (or one of its subtrees)."""
        components = path_info.components
        if idx == len(components):
          self.path_info = path_info
          self.explicit |= (
              path_info.HasField("stat_entry") or
              path_info.HasField("hash_entry"))
        else:
          child = self.children.setdefault(components[idx], TrieNode())
          child.Add(path_info, idx=idx + 1)
          self.explicit |= child.explicit

      def Collect(self, path_infos):
        if self.path_info is not None and self.explicit:
          path_infos.append(self.path_info)

        for component in sorted(self.children):
          self.children[component].Collect(path_infos)

    trie = TrieNode()
    for path_info in result:
      trie.Add(path_info)

    explicit_path_infos = []
    trie.Collect(explicit_path_infos)
    return explicit_path_infos

  def _GetPathRecord(self, client_id, path_info, set_default=True):
    components = tuple(path_info.components)
    path_idx = (client_id, path_info.path_type, components)

    if set_default:
      default = _PathRecord(
          path_type=path_info.path_type, components=components)
      return self.path_records.setdefault(path_idx, default)
    else:
      return self.path_records.get(path_idx, None)

  def _WritePathInfo(self, client_id, path_info):
    """Writes a single path info record for given client."""
    path_record = self._GetPathRecord(client_id, path_info)
    path_record.AddPathInfo(path_info)

    parent_path_info = path_info.GetParent()
    if parent_path_info is not None:
      parent_path_record = self._GetPathRecord(client_id, parent_path_info)
      parent_path_record.AddChild(path_info)

  @utils.Synchronized
  def WritePathInfos(self, client_id, path_infos):
    if client_id not in self.metadatas:
      raise db.UnknownClientError(client_id)

    for path_info in path_infos:
      self._WritePathInfo(client_id, path_info)
      for ancestor_path_info in path_info.GetAncestors():
        self._WritePathInfo(client_id, ancestor_path_info)

  @utils.Synchronized
  def ReadPathInfosHistories(
      self,
      client_id: Text,
      path_type: rdf_objects.PathInfo.PathType,
      components_list: Iterable[Sequence[Text]],
      cutoff: Optional[rdfvalue.RDFDatetime] = None
  ) -> Dict[Sequence[Text], Sequence[rdf_objects.PathInfo]]:
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

      results[components] = []
      for timestamp in sorted(entries_by_ts):
        if cutoff is not None and timestamp > cutoff:
          continue

        results[components].append(entries_by_ts[timestamp])

    return results

  @utils.Synchronized
  def ReadLatestPathInfosWithHashBlobReferences(self,
                                                client_paths,
                                                max_timestamp=None):
    """Returns PathInfos that have corresponding HashBlobReferences."""

    results = {}
    for cp in client_paths:
      results[cp] = None

      try:
        path_record = self.path_records[(cp.client_id, cp.path_type,
                                         cp.components)]
      except KeyError:
        continue

      stat_entries_by_ts = {
          ts: stat_entry for ts, stat_entry in path_record.GetStatEntries()
      }

      for ts, hash_entry in sorted(
          path_record.GetHashEntries(), key=lambda e: e[0], reverse=True):
        if max_timestamp is not None and ts > max_timestamp:
          continue

        hash_id = rdf_objects.SHA256HashID.FromSerializedBytes(
            hash_entry.sha256.AsBytes())
        if hash_id not in self.blob_refs_by_hashes:
          continue

        pi = rdf_objects.PathInfo(
            path_type=cp.path_type,
            components=cp.components,
            timestamp=ts,
            hash_entry=hash_entry)
        try:
          pi.stat_entry = stat_entries_by_ts[ts]
        except KeyError:
          pass

        results[cp] = pi
        break

    return results
