#!/usr/bin/env python
# Lint as: python3
"""The in memory database methods for client handling."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from typing import Generator, List, Text

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_stats as rdf_client_stats
from grr_response_core.lib.util import collection
from grr_response_server import fleet_utils
from grr_response_server.databases import db
from grr_response_server.rdfvalues import objects as rdf_objects


class InMemoryDBClientMixin(object):
  """InMemoryDB mixin for client related functions."""

  @utils.Synchronized
  def WriteClientMetadata(self,
                          client_id,
                          certificate=None,
                          fleetspeak_enabled=None,
                          first_seen=None,
                          last_ping=None,
                          last_clock=None,
                          last_ip=None,
                          last_foreman=None):
    """Write metadata about the client."""
    md = {}
    if certificate is not None:
      md["certificate"] = certificate

    if fleetspeak_enabled is not None:
      md["fleetspeak_enabled"] = fleetspeak_enabled

    if first_seen is not None:
      md["first_seen"] = first_seen

    if last_ping is not None:
      md["ping"] = last_ping

    if last_clock is not None:
      md["clock"] = last_clock

    if last_ip is not None:
      md["ip"] = last_ip

    if last_foreman is not None:
      md["last_foreman_time"] = last_foreman

    if not md:
      raise ValueError("NOOP write.")

    self.metadatas.setdefault(client_id, {}).update(md)

  @utils.Synchronized
  def MultiReadClientMetadata(self, client_ids):
    """Reads ClientMetadata records for a list of clients."""
    res = {}
    for client_id in client_ids:
      md = self.metadatas.get(client_id, None)
      if md is None:
        continue

      res[client_id] = rdf_objects.ClientMetadata(
          certificate=md.get("certificate"),
          fleetspeak_enabled=md.get("fleetspeak_enabled"),
          first_seen=md.get("first_seen"),
          ping=md.get("ping"),
          clock=md.get("clock"),
          ip=md.get("ip"),
          last_foreman_time=md.get("last_foreman_time"),
          last_crash_timestamp=md.get("last_crash_timestamp"),
          startup_info_timestamp=md.get("startup_info_timestamp"))

    return res

  @utils.Synchronized
  def WriteClientSnapshot(self, snapshot):
    """Writes new client snapshot."""
    client_id = snapshot.client_id

    if client_id not in self.metadatas:
      raise db.UnknownClientError(client_id)

    startup_info = snapshot.startup_info
    snapshot.startup_info = None

    ts = rdfvalue.RDFDatetime.Now()
    history = self.clients.setdefault(client_id, {})
    history[ts] = snapshot.SerializeToBytes()

    history = self.startup_history.setdefault(client_id, {})
    history[ts] = startup_info.SerializeToBytes()

    snapshot.startup_info = startup_info

  @utils.Synchronized
  def MultiReadClientSnapshot(self, client_ids):
    """Reads the latest client snapshots for a list of clients."""
    res = {}
    for client_id in client_ids:
      history = self.clients.get(client_id, None)
      if not history:
        res[client_id] = None
        continue
      last_timestamp = max(history)
      last_serialized = history[last_timestamp]
      client_obj = rdf_objects.ClientSnapshot.FromSerializedBytes(
          last_serialized)
      client_obj.timestamp = last_timestamp
      client_obj.startup_info = rdf_client.StartupInfo.FromSerializedBytes(
          self.startup_history[client_id][last_timestamp])
      res[client_id] = client_obj
    return res

  @utils.Synchronized
  def MultiReadClientFullInfo(self, client_ids, min_last_ping=None):
    """Reads full client information for a list of clients."""
    res = {}
    for client_id in client_ids:
      try:
        md = self.ReadClientMetadata(client_id)
      except db.UnknownClientError:
        continue

      if md and min_last_ping and md.ping < min_last_ping:
        continue
      last_snapshot = self.ReadClientSnapshot(client_id)
      full_info = rdf_objects.ClientFullInfo(
          metadata=md,
          labels=self.ReadClientLabels(client_id),
          last_startup_info=self.ReadClientStartupInfo(client_id))
      if last_snapshot is None:
        full_info.last_snapshot = rdf_objects.ClientSnapshot(
            client_id=client_id)
      else:
        full_info.last_snapshot = last_snapshot
      res[client_id] = full_info
    return res

  @utils.Synchronized
  def ReadClientLastPings(self,
                          min_last_ping=None,
                          max_last_ping=None,
                          fleetspeak_enabled=None,
                          batch_size=db.CLIENT_IDS_BATCH_SIZE):
    """Yields dicts of last-ping timestamps for clients in the DB."""
    last_pings = {}
    for client_id, metadata in self.metadatas.items():
      last_ping = metadata.get("ping", rdfvalue.RDFDatetime(0))
      is_fleetspeak_client = metadata.get("fleetspeak_enabled", False)
      if min_last_ping is not None and last_ping < min_last_ping:
        continue
      elif max_last_ping is not None and last_ping > max_last_ping:
        continue
      elif (fleetspeak_enabled is not None and
            is_fleetspeak_client != fleetspeak_enabled):
        continue
      else:
        last_pings[client_id] = metadata.get("ping", None)

        if len(last_pings) == batch_size:
          yield last_pings
          last_pings = {}

    if last_pings:
      yield last_pings

  @utils.Synchronized
  def WriteClientSnapshotHistory(self, clients):
    """Writes the full history for a particular client."""
    if clients[0].client_id not in self.metadatas:
      raise db.UnknownClientError(clients[0].client_id)

    for client in clients:
      startup_info = client.startup_info
      client.startup_info = None

      snapshots = self.clients.setdefault(client.client_id, {})
      snapshots[client.timestamp] = client.SerializeToBytes()

      startup_infos = self.startup_history.setdefault(client.client_id, {})
      startup_infos[client.timestamp] = startup_info.SerializeToBytes()

      client.startup_info = startup_info

  @utils.Synchronized
  def ReadClientSnapshotHistory(self, client_id, timerange=None):
    """Reads the full history for a particular client."""
    from_time, to_time = self._ParseTimeRange(timerange)

    history = self.clients.get(client_id)
    if not history:
      return []
    res = []
    for ts in sorted(history, reverse=True):
      if ts < from_time or ts > to_time:
        continue

      client_obj = rdf_objects.ClientSnapshot.FromSerializedBytes(history[ts])
      client_obj.timestamp = ts
      client_obj.startup_info = rdf_client.StartupInfo.FromSerializedBytes(
          self.startup_history[client_id][ts])
      res.append(client_obj)
    return res

  @utils.Synchronized
  def AddClientKeywords(self, client_id, keywords):
    """Associates the provided keywords with the client."""
    if client_id not in self.metadatas:
      raise db.UnknownClientError(client_id)

    for kw in keywords:
      self.keywords.setdefault(kw, {})
      self.keywords[kw][client_id] = rdfvalue.RDFDatetime.Now()

  @utils.Synchronized
  def ListClientsForKeywords(self, keywords, start_time=None):
    """Lists the clients associated with keywords."""
    res = {kw: [] for kw in keywords}
    for kw in keywords:
      for client_id, timestamp in self.keywords.get(kw, {}).items():
        if start_time is not None and timestamp < start_time:
          continue
        res[kw].append(client_id)
    return res

  @utils.Synchronized
  def RemoveClientKeyword(self, client_id, keyword):
    """Removes the association of a particular client to a keyword."""
    if keyword in self.keywords and client_id in self.keywords[keyword]:
      del self.keywords[keyword][client_id]

  @utils.Synchronized
  def AddClientLabels(self, client_id, owner, labels):
    """Attaches a user label to a client."""
    if client_id not in self.metadatas:
      raise db.UnknownClientError(client_id)

    labelset = self.labels.setdefault(client_id, {}).setdefault(owner, set())
    for l in labels:
      labelset.add(utils.SmartUnicode(l))

  @utils.Synchronized
  def MultiReadClientLabels(self, client_ids):
    """Reads the user labels for a list of clients."""
    res = {}
    for client_id in client_ids:
      res[client_id] = []
      owner_dict = self.labels.get(client_id, {})
      for owner, labels in owner_dict.items():
        for l in labels:
          res[client_id].append(rdf_objects.ClientLabel(owner=owner, name=l))
      res[client_id].sort(key=lambda label: (label.owner, label.name))
    return res

  @utils.Synchronized
  def RemoveClientLabels(self, client_id, owner, labels):
    """Removes a list of user labels from a given client."""
    labelset = self.labels.setdefault(client_id, {}).setdefault(owner, set())
    for l in labels:
      labelset.discard(utils.SmartUnicode(l))

  @utils.Synchronized
  def ReadAllClientLabels(self):
    """Lists all client labels known to the system."""
    results = {}
    for labels_dict in self.labels.values():
      for owner, names in labels_dict.items():
        for name in names:
          results[(owner, name)] = rdf_objects.ClientLabel(
              owner=owner, name=name)
    return list(results.values())

  @utils.Synchronized
  def WriteClientStartupInfo(self, client_id, startup_info):
    """Writes a new client startup record."""
    if client_id not in self.metadatas:
      raise db.UnknownClientError(client_id)

    ts = rdfvalue.RDFDatetime.Now()
    self.metadatas[client_id]["startup_info_timestamp"] = ts
    history = self.startup_history.setdefault(client_id, {})
    history[ts] = startup_info.SerializeToBytes()

  @utils.Synchronized
  def ReadClientStartupInfo(self, client_id):
    """Reads the latest client startup record for a single client."""
    history = self.startup_history.get(client_id, None)
    if not history:
      return None

    ts = max(history)
    res = rdf_client.StartupInfo.FromSerializedBytes(history[ts])
    res.timestamp = ts
    return res

  @utils.Synchronized
  def ReadClientStartupInfoHistory(self, client_id, timerange=None):
    """Reads the full startup history for a particular client."""
    from_time, to_time = self._ParseTimeRange(timerange)

    history = self.startup_history.get(client_id)
    if not history:
      return []
    res = []
    for ts in sorted(history, reverse=True):
      if ts < from_time or ts > to_time:
        continue

      client_data = rdf_client.StartupInfo.FromSerializedBytes(history[ts])
      client_data.timestamp = ts
      res.append(client_data)
    return res

  @utils.Synchronized
  def WriteClientCrashInfo(self, client_id, crash_info):
    """Writes a new client crash record."""
    if client_id not in self.metadatas:
      raise db.UnknownClientError(client_id)

    ts = rdfvalue.RDFDatetime.Now()
    self.metadatas[client_id]["last_crash_timestamp"] = ts
    history = self.crash_history.setdefault(client_id, {})
    history[ts] = crash_info.SerializeToBytes()

  @utils.Synchronized
  def ReadClientCrashInfo(self, client_id):
    """Reads the latest client crash record for a single client."""
    history = self.crash_history.get(client_id, None)
    if not history:
      return None

    ts = max(history)
    res = rdf_client.ClientCrash.FromSerializedBytes(history[ts])
    res.timestamp = ts
    return res

  @utils.Synchronized
  def ReadClientCrashInfoHistory(self, client_id):
    """Reads the full crash history for a particular client."""
    history = self.crash_history.get(client_id)
    if not history:
      return []
    res = []
    for ts in sorted(history, reverse=True):
      client_data = rdf_client.ClientCrash.FromSerializedBytes(history[ts])
      client_data.timestamp = ts
      res.append(client_data)
    return res

  @utils.Synchronized
  def WriteClientStats(self, client_id: Text,
                       stats: rdf_client_stats.ClientStats) -> None:
    """Stores a ClientStats instance."""
    if client_id not in collection.Flatten(self.ReadAllClientIDs()):
      raise db.UnknownClientError(client_id)

    if stats.timestamp is None:
      stats.timestamp = rdfvalue.RDFDatetime.Now()

    copy = rdf_client_stats.ClientStats(stats)
    self.client_stats[client_id][copy.timestamp] = copy

  @utils.Synchronized
  def ReadClientStats(
      self, client_id: Text, min_timestamp: rdfvalue.RDFDatetime,
      max_timestamp: rdfvalue.RDFDatetime
  ) -> List[rdf_client_stats.ClientStats]:
    """Reads ClientStats for a given client and time range."""
    results = []
    for timestamp, stats in self.client_stats[client_id].items():
      if min_timestamp <= timestamp <= max_timestamp:
        results.append(rdf_client_stats.ClientStats(stats))
    return results

  @utils.Synchronized
  def DeleteOldClientStats(
      self, yield_after_count: int,
      retention_time: rdfvalue.RDFDatetime) -> Generator[int, None, None]:
    """Deletes ClientStats older than a given timestamp."""
    deleted_count = 0

    for stats_dict in self.client_stats.values():
      for timestamp in list(stats_dict.keys()):
        if timestamp < retention_time:
          del stats_dict[timestamp]
          deleted_count += 1

          if deleted_count >= yield_after_count:
            yield deleted_count
            deleted_count = 0

    if deleted_count > 0:
      yield deleted_count

  @utils.Synchronized
  def CountClientVersionStringsByLabel(self, day_buckets):
    """Computes client-activity stats for all GRR versions in the DB."""

    def ExtractVersion(client_info):
      return client_info.last_snapshot.GetGRRVersionString()

    return self._CountClientStatisticByLabel(day_buckets, ExtractVersion)

  @utils.Synchronized
  def CountClientPlatformsByLabel(self, day_buckets):
    """Computes client-activity stats for all client platforms in the DB."""

    def ExtractPlatform(client_info):
      return client_info.last_snapshot.knowledge_base.os

    return self._CountClientStatisticByLabel(day_buckets, ExtractPlatform)

  @utils.Synchronized
  def CountClientPlatformReleasesByLabel(self, day_buckets):
    """Computes client-activity stats for OS-release strings in the DB."""
    return self._CountClientStatisticByLabel(
        day_buckets, lambda client_info: client_info.last_snapshot.Uname())

  def _CountClientStatisticByLabel(self, day_buckets, extract_statistic_fn):
    """Returns client-activity metrics for a particular statistic.

    Args:
      day_buckets: A set of n-day-active buckets.
      extract_statistic_fn: A function that extracts the statistic's value from
        a ClientFullInfo object.
    """
    fleet_stats_builder = fleet_utils.FleetStatsBuilder(day_buckets)
    now = rdfvalue.RDFDatetime.Now()
    for info in self.IterateAllClientsFullInfo(batch_size=db.MAX_COUNT):
      if not info.metadata.ping:
        continue
      statistic_value = extract_statistic_fn(info)

      for day_bucket in day_buckets:
        time_boundary = now - rdfvalue.Duration.From(day_bucket, rdfvalue.DAYS)
        if info.metadata.ping > time_boundary:
          # Count the client if it has been active in the last 'day_bucket'
          # days.
          fleet_stats_builder.IncrementTotal(statistic_value, day_bucket)
          for client_label in info.GetLabelsNames(owner="GRR"):
            fleet_stats_builder.IncrementLabel(client_label, statistic_value,
                                               day_bucket)
    return fleet_stats_builder.Build()

  @utils.Synchronized
  def DeleteClient(self, client_id):
    """Deletes a client with all associated metadata."""
    try:
      del self.metadatas[client_id]
    except KeyError:
      raise db.UnknownClientError(client_id)

    self.clients.pop(client_id, None)

    self.labels.pop(client_id, None)

    self.startup_history.pop(client_id, None)

    self.crash_history.pop(client_id, None)

    self.client_stats.pop(client_id, None)

    for key in [k for k in self.flows if k[0] == client_id]:
      self.flows.pop(key)
    for key in [k for k in self.flow_requests if k[0] == client_id]:
      self.flow_requests.pop(key)
    for key in [k for k in self.flow_processing_requests if k[0] == client_id]:
      self.flow_processing_requests.pop(key)
    for key in [k for k in self.client_action_requests if k[0] == client_id]:
      self.client_action_requests.pop(key)

    for kw in self.keywords:
      self.keywords[kw].pop(client_id, None)
