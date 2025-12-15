#!/usr/bin/env python
"""The in memory database methods for path handling."""

from collections.abc import Collection, Iterable, Sequence
from typing import Any, Optional, Union

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.util import collection
from grr_response_proto import jobs_pb2
from grr_response_proto import objects_pb2
from grr_response_server.databases import db
from grr_response_server.models import paths as models_paths
from grr_response_server.rdfvalues import objects as rdf_objects


class _PathRecord:
  """A class representing all known information about particular path.

  Attributes:
    path_type: A path type of the path that this record corresponds to.
    components: A path components of the path that this record corresponds to.
  """

  def __init__(
      self,
      path_type: objects_pb2.PathInfo.PathType,
      components: tuple[str, ...],
  ):
    self._path_type: objects_pb2.PathInfo.PathType = path_type
    self._components = components

    # Maps timestamp micros since epoch to a path info object.
    self._path_infos: dict[int, objects_pb2.PathInfo] = {}

  @property
  def _stat_entries(self) -> dict[int, jobs_pb2.StatEntry]:
    res = {}
    for ts, pi in self._path_infos.items():
      if pi.HasField("stat_entry"):
        res[ts] = pi.stat_entry
    return res

  @property
  def _hash_entries(self) -> dict[int, jobs_pb2.Hash]:
    return {
        ts: pi.hash_entry
        for ts, pi in self._path_infos.items()
        if pi.HasField("hash_entry")
    }

  def GetStatEntries(self) -> Iterable[tuple[int, jobs_pb2.StatEntry]]:
    return self._stat_entries.items()

  def GetHashEntries(self) -> Iterable[tuple[int, jobs_pb2.Hash]]:
    return self._hash_entries.items()

  def AddPathInfo(self, path_info: objects_pb2.PathInfo) -> None:
    """Updates existing path information of the path record."""

    if self._path_type != path_info.path_type:
      message = "Incompatible path types: `%s` and `%s`"
      raise ValueError(message % (self._path_type, path_info.path_type))
    if self._components != tuple(path_info.components):
      message = "Incompatible path components: `%s` and `%s`"
      raise ValueError(message % (self._components, path_info.components))

    if (
        path_info.HasField("timestamp")
        and path_info.timestamp in self._path_infos
    ):
      raise ValueError(
          "PathInfo with timestamp %r was added before." % path_info.timestamp
      )

    new_path_info = objects_pb2.PathInfo()
    new_path_info.CopyFrom(path_info)
    if not new_path_info.HasField("timestamp"):
      new_path_info.timestamp = (
          rdfvalue.RDFDatetime.Now().AsMicrosecondsSinceEpoch()
      )
    self._path_infos[new_path_info.timestamp] = new_path_info

  def GetPathInfo(
      self, timestamp: Optional[int] = None
  ) -> objects_pb2.PathInfo:
    """Generates a summary about the path record.

    Args:
      timestamp: A point in time from which the data should be retrieved.

    Returns:
      A `objects_pb2.PathInfo` instance.
    """
    path_info_timestamp = self._LastEntryTimestamp(self._path_infos, timestamp)
    try:
      result = objects_pb2.PathInfo()
      result.CopyFrom(self._path_infos[path_info_timestamp])
    except KeyError:
      result = objects_pb2.PathInfo(
          path_type=self._path_type, components=self._components, directory=True
      )

    stat_entry_timestamp = self._LastEntryTimestamp(
        self._stat_entries, timestamp
    )
    if stat_entry_timestamp:
      result.last_stat_entry_timestamp = stat_entry_timestamp
    stat_entry = self._stat_entries.get(stat_entry_timestamp)
    if stat_entry:
      result.stat_entry.CopyFrom(stat_entry)

    hash_entry_timestamp = self._LastEntryTimestamp(
        self._hash_entries, timestamp
    )
    if hash_entry_timestamp:
      result.last_hash_entry_timestamp = hash_entry_timestamp
    hash_entry = self._hash_entries.get(hash_entry_timestamp)
    if hash_entry:
      result.hash_entry.CopyFrom(hash_entry)

    return result

  @staticmethod
  def _LastEntryTimestamp(
      dct: dict[
          int, Union[objects_pb2.PathInfo, jobs_pb2.StatEntry, jobs_pb2.Hash]
      ],
      upper_bound_timestamp: Optional[int],
  ) -> Optional[int]:
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

  # Maps (client_id, path_type, components) to a path record.
  path_records: dict[
      tuple[str, "objects_pb2.PathInfo.PathType", tuple[str, ...]], _PathRecord
  ]

  # Maps client_id to client metadata.
  metadatas: dict[str, Any]

  # Maps hash_id to a list of blob references.
  blob_refs_by_hashes: dict[
      rdf_objects.SHA256HashID, list[objects_pb2.BlobReference]
  ]

  @utils.Synchronized
  def ReadPathInfo(
      self,
      client_id: str,
      path_type: objects_pb2.PathInfo.PathType,
      components: Sequence[str],
      timestamp: Optional[rdfvalue.RDFDatetime] = None,
  ) -> objects_pb2.PathInfo:
    """Retrieves a path info record for a given path."""
    try:
      path_record = self.path_records[(client_id, path_type, tuple(components))]
      return path_record.GetPathInfo(timestamp=timestamp)
    except KeyError:
      raise db.UnknownPathError(
          client_id=client_id, path_type=path_type, components=components
      )

  @utils.Synchronized
  def ReadPathInfos(
      self,
      client_id: str,
      path_type: objects_pb2.PathInfo.PathType,
      components_list: Collection[Sequence[str]],
  ) -> dict[tuple[str, ...], Optional[objects_pb2.PathInfo]]:
    """Retrieves path info records for given paths."""
    result = {}

    for components in components_list:
      try:
        path_record = self.path_records[
            (client_id, path_type, tuple(components))
        ]
        result[tuple(components)] = path_record.GetPathInfo()
      except KeyError:
        result[tuple(components)] = None

    return result

  @utils.Synchronized
  def ListDescendantPathInfos(
      self,
      client_id: str,
      path_type: objects_pb2.PathInfo.PathType,
      components: Sequence[str],
      timestamp: Optional[rdfvalue.RDFDatetime] = None,
      max_depth: Optional[int] = None,
  ) -> Sequence[objects_pb2.PathInfo]:
    """Lists path info records that correspond to children of given path."""
    result = []
    root_dir_exists = False

    for path_idx, path_record in self.path_records.items():
      other_client_id, other_path_type, other_components = path_idx
      path_info = path_record.GetPathInfo(
          timestamp=timestamp.AsMicrosecondsSinceEpoch()
          if timestamp is not None
          else None
      )

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
      if (
          max_depth is not None
          and len(other_components) - len(components) > max_depth
      ):
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
          self.explicit |= path_info.HasField(
              "stat_entry"
          ) or path_info.HasField("hash_entry")
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

  def _GetPathRecord(
      self, client_id: str, path_info: objects_pb2.PathInfo
  ) -> _PathRecord:
    """Returns the _PathRecord for the given client and path info."""
    components = tuple(path_info.components)
    path_idx = (client_id, path_info.path_type, components)

    default = _PathRecord(path_type=path_info.path_type, components=components)
    return self.path_records.setdefault(path_idx, default)

  def _WritePathInfo(
      self, client_id: str, path_info: objects_pb2.PathInfo
  ) -> None:
    """Writes a single path info record for given client."""
    path_record = self._GetPathRecord(client_id, path_info)
    path_record.AddPathInfo(path_info)

  @utils.Synchronized
  def WritePathInfos(
      self,
      client_id: str,
      path_infos: Iterable[objects_pb2.PathInfo],
  ) -> None:
    """Writes a collection of path_info records for a client."""
    if client_id not in self.metadatas:
      raise db.UnknownClientError(client_id)

    for path_info in path_infos:
      self._WritePathInfo(client_id, path_info)
      for ancestor_path_info in models_paths.GetAncestorPathInfos(path_info):
        self._WritePathInfo(client_id, ancestor_path_info)

  @utils.Synchronized
  def ReadPathInfosHistories(
      self,
      client_id: str,
      path_type: objects_pb2.PathInfo.PathType,
      components_list: Iterable[Sequence[str]],
      cutoff: Optional[rdfvalue.RDFDatetime] = None,
  ) -> dict[tuple[str, ...], Sequence[objects_pb2.PathInfo]]:
    """Reads a collection of hash and stat entries for given paths."""
    results = {}

    for components in components_list:
      components = tuple(components)
      try:
        path_record = self.path_records[(client_id, path_type, components)]
      except KeyError:
        results[components] = []
        continue

      entries_by_ts = {}
      for ts, stat_entry in path_record.GetStatEntries():
        pi = objects_pb2.PathInfo(
            path_type=path_type,
            components=components,
            timestamp=ts,
            stat_entry=stat_entry,
        )
        entries_by_ts[ts] = pi

      for ts, hash_entry in path_record.GetHashEntries():
        try:
          pi = entries_by_ts[ts]
        except KeyError:
          pi = objects_pb2.PathInfo(
              path_type=path_type, components=components, timestamp=ts
          )
          entries_by_ts[ts] = pi

        pi.hash_entry.CopyFrom(hash_entry)

      results[components] = []
      cutoff_micros = (
          cutoff.AsMicrosecondsSinceEpoch() if cutoff is not None else None
      )
      for timestamp in sorted(entries_by_ts):
        if cutoff is not None and timestamp > cutoff_micros:
          continue

        results[components].append(entries_by_ts[timestamp])

    return results

  @utils.Synchronized
  def ReadLatestPathInfosWithHashBlobReferences(
      self,
      client_paths: Collection[db.ClientPath],
      max_timestamp: Optional[rdfvalue.RDFDatetime] = None,
  ) -> dict[db.ClientPath, Optional[objects_pb2.PathInfo]]:
    """Returns PathInfos that have corresponding HashBlobReferences."""

    results = {}
    for cp in client_paths:
      results[cp] = None

      try:
        path_record = self.path_records[
            (cp.client_id, cp.path_type, tuple(cp.components))
        ]
      except KeyError:
        continue

      stat_entries_by_ts = {
          ts: stat_entry for ts, stat_entry in path_record.GetStatEntries()
      }

      for ts, hash_entry in sorted(
          path_record.GetHashEntries(), key=lambda e: e[0], reverse=True
      ):
        if (
            max_timestamp is not None
            and ts > max_timestamp.AsMicrosecondsSinceEpoch()
        ):
          continue

        hash_id = rdf_objects.SHA256HashID.FromSerializedBytes(
            hash_entry.sha256
        )
        if hash_id not in self.blob_refs_by_hashes:
          continue

        pi = objects_pb2.PathInfo(
            path_type=cp.path_type,
            components=tuple(cp.components),
            timestamp=ts,
        )
        pi.hash_entry.CopyFrom(hash_entry)
        try:
          pi.stat_entry.CopyFrom(stat_entries_by_ts[ts])
        except KeyError:
          pass

        results[cp] = pi
        break

    return results
