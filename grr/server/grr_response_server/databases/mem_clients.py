#!/usr/bin/env python
"""The in memory database methods for client handling."""

from collections.abc import Collection, Iterator, Mapping, Sequence
from typing import Optional, TypedDict

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import crypto as rdf_crypto
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_proto import objects_pb2
from grr_response_server.databases import db
from grr_response_server.models import clients as models_clients
from grr_response_proto.rrg import startup_pb2 as rrg_startup_pb2


class _MetadataDict(TypedDict, total=False):
  certificate: rdf_crypto.RDFX509Cert
  first_seen: rdfvalue.RDFDatetime
  ping: rdfvalue.RDFDatetime
  clock: rdfvalue.RDFDatetime
  ip: jobs_pb2.NetworkAddress
  last_foreman_time: rdfvalue.RDFDatetime
  last_crash_timestamp: rdfvalue.RDFDatetime
  startup_info_timestamp: rdfvalue.RDFDatetime
  last_fleetspeak_validation_info: Optional[
      bytes  # Serialized `jobs_pb2.FleetspeakValidationInfo`.
  ]


class InMemoryDBClientMixin(object):
  """InMemoryDB mixin for client related functions."""

  clients: dict[
      str, dict[rdfvalue.RDFDatetime, bytes]
  ]  # Serialized `objects_pb2.ClientSnapshot`.
  metadatas: dict[str, _MetadataDict]
  startup_history: dict[
      str, dict[rdfvalue.RDFDatetime, bytes]
  ]  # Serialized `jobs_pb2.StartupInfo`.
  crash_history: dict[
      str, dict[rdfvalue.RDFDatetime, bytes]
  ]  # Serialized `jobs_pb2.ClientCrash`.
  rrg_startups: dict[str, list[rrg_startup_pb2.Startup]]
  labels: dict[str, dict[str, set[str]]]
  keywords: dict[str, dict[str, rdfvalue.RDFDatetime]]
  flows: dict[tuple[str, str], flows_pb2.Flow]
  flow_requests: dict[tuple[str, str], dict[str, flows_pb2.FlowRequest]]
  flow_processing_requests: dict[
      tuple[str, str, str], flows_pb2.FlowProcessingRequest
  ]
  users: dict[str, objects_pb2.GRRUser]

  @utils.Synchronized
  def MultiWriteClientMetadata(
      self,
      client_ids: Collection[str],
      first_seen: Optional[rdfvalue.RDFDatetime] = None,
      last_ping: Optional[rdfvalue.RDFDatetime] = None,
      last_foreman: Optional[rdfvalue.RDFDatetime] = None,
      fleetspeak_validation_info: Optional[Mapping[str, str]] = None,
  ) -> None:
    """Writes metadata about the clients."""
    md = {}
    if first_seen is not None:
      md["first_seen"] = first_seen

    if last_ping is not None:
      md["ping"] = last_ping

    if last_foreman is not None:
      md["last_foreman_time"] = last_foreman

    if fleetspeak_validation_info is not None:
      if fleetspeak_validation_info:
        pb = models_clients.FleetspeakValidationInfoFromDict(
            fleetspeak_validation_info
        )
        md["last_fleetspeak_validation_info"] = pb.SerializeToString()
      else:
        # Write null for empty or non-existent validation info.
        md["last_fleetspeak_validation_info"] = None

    for client_id in client_ids:
      self.metadatas.setdefault(client_id, {}).update(md)

  @utils.Synchronized
  def MultiReadClientMetadata(
      self,
      client_ids: Collection[str],
  ) -> Mapping[str, objects_pb2.ClientMetadata]:
    """Reads ClientMetadata records for a list of clients."""
    res = {}
    for client_id in client_ids:
      md = self.metadatas.get(client_id, None)
      if md is None:
        continue

      metadata = objects_pb2.ClientMetadata()
      if (certificate := md.get("certificate")) is not None:
        metadata.certificate = certificate.SerializeToBytes()
      if (first_seen := md.get("first_seen")) is not None:
        metadata.first_seen = int(first_seen)
      if ping := md.get("ping"):
        metadata.ping = int(ping)
      if (last_foreman_time := md.get("last_foreman_time")) is not None:
        metadata.last_foreman_time = int(last_foreman_time)
      if (last_crash_timestamp := md.get("last_crash_timestamp")) is not None:
        metadata.last_crash_timestamp = int(last_crash_timestamp)
      if (startup_info_time := md.get("startup_info_timestamp")) is not None:
        metadata.startup_info_timestamp = int(startup_info_time)
      if (fsvi := md.get("last_fleetspeak_validation_info")) is not None:
        metadata.last_fleetspeak_validation_info.ParseFromString(fsvi)

      res[client_id] = metadata

    return res

  @utils.Synchronized
  def WriteClientSnapshot(
      self,
      snapshot: objects_pb2.ClientSnapshot,
  ) -> None:
    """Writes new client snapshot."""
    client_id = snapshot.client_id

    if client_id not in self.metadatas:
      raise db.UnknownClientError(client_id)

    startup_info = jobs_pb2.StartupInfo()
    startup_info.MergeFrom(snapshot.startup_info)

    snapshot_without_startup_info = objects_pb2.ClientSnapshot()
    snapshot_without_startup_info.CopyFrom(snapshot)
    snapshot_without_startup_info.ClearField("startup_info")

    ts = rdfvalue.RDFDatetime.Now()
    history = self.clients.setdefault(client_id, {})
    history[ts] = snapshot_without_startup_info.SerializeToString()

    history = self.startup_history.setdefault(client_id, {})
    history[ts] = startup_info.SerializeToString()

  @utils.Synchronized
  def MultiReadClientSnapshot(
      self,
      client_ids: Collection[str],
  ) -> Mapping[str, Optional[objects_pb2.ClientSnapshot]]:
    """Reads the latest client snapshots for a list of clients."""
    res = {}
    for client_id in client_ids:
      history = self.clients.get(client_id, None)
      if not history:
        res[client_id] = None
        continue
      last_timestamp = max(history)

      last_snapshot_bytes = history[last_timestamp]
      last_startup_bytes = self.startup_history[client_id][last_timestamp]

      last_snapshot = objects_pb2.ClientSnapshot()
      last_snapshot.ParseFromString(last_snapshot_bytes)
      last_snapshot.startup_info.ParseFromString(last_startup_bytes)
      last_snapshot.timestamp = int(last_timestamp)

      res[client_id] = last_snapshot
    return res

  @utils.Synchronized
  def MultiReadClientFullInfo(
      self,
      client_ids: Collection[str],
      min_last_ping: Optional[rdfvalue.RDFDatetime] = None,
  ) -> Mapping[str, objects_pb2.ClientFullInfo]:
    """Reads full client information for a list of clients."""
    res = {}
    for client_id in client_ids:
      try:
        # ReadClientMetadata is implemented in the db.Database class.
        md = self.ReadClientMetadata(client_id)  # pytype: disable=attribute-error
      except db.UnknownClientError:
        continue

      if md and min_last_ping and rdfvalue.RDFDatetime(md.ping) < min_last_ping:
        continue
      # ReadClientSnapshot is implemented in the db.Database class.
      last_snapshot = self.ReadClientSnapshot(client_id)  # pytype: disable=attribute-error

      full_info = objects_pb2.ClientFullInfo()
      full_info.metadata.CopyFrom(md)
      # ReadClientLabels is implemented in the db.Database class.
      full_info.labels.extend(self.ReadClientLabels(client_id))  # pytype: disable=attribute-error

      if last_snapshot is None:
        full_info.last_snapshot.client_id = client_id
      else:
        full_info.last_snapshot.CopyFrom(last_snapshot)

      if (startup_info := self.ReadClientStartupInfo(client_id)) is not None:
        full_info.last_startup_info.CopyFrom(startup_info)

      if self.rrg_startups[client_id]:
        last_rrg_startup = self.rrg_startups[client_id][-1]
        last_rrg_startup_bytes = last_rrg_startup.SerializeToString()

        full_info.last_rrg_startup.ParseFromString(last_rrg_startup_bytes)

      res[client_id] = full_info

    return res

  @utils.Synchronized
  def ReadClientLastPings(
      self,
      min_last_ping: Optional[rdfvalue.RDFDatetime] = None,
      max_last_ping: Optional[rdfvalue.RDFDatetime] = None,
      batch_size: int = db.CLIENT_IDS_BATCH_SIZE,
  ) -> Iterator[Mapping[str, Optional[rdfvalue.RDFDatetime]]]:
    """Yields dicts of last-ping timestamps for clients in the DB."""
    last_pings = {}
    for client_id, metadata in self.metadatas.items():
      last_ping = metadata.get("ping", rdfvalue.RDFDatetime(0))
      if min_last_ping is not None and last_ping < min_last_ping:
        continue
      elif max_last_ping is not None and last_ping > max_last_ping:
        continue
      else:
        last_pings[client_id] = metadata.get("ping", None)

        if len(last_pings) == batch_size:
          yield last_pings
          last_pings = {}

    if last_pings:
      yield last_pings

  @utils.Synchronized
  def ReadClientSnapshotHistory(
      self,
      client_id: str,
      timerange: Optional[
          tuple[Optional[rdfvalue.RDFDatetime], Optional[rdfvalue.RDFDatetime]]
      ] = None,
  ) -> Sequence[objects_pb2.ClientSnapshot]:
    """Reads the full history for a particular client."""
    # _ParseTimeRange is implemented in InMemoryDB class that uses this mixin.
    from_time, to_time = self._ParseTimeRange(timerange)  # pytype: disable=attribute-error

    history = self.clients.get(client_id)
    if not history:
      return []
    res = []
    for ts in sorted(history, reverse=True):
      if ts < from_time or ts > to_time:
        continue

      snapshot_bytes = history[ts]
      startup_bytes = self.startup_history[client_id][ts]

      snapshot = objects_pb2.ClientSnapshot()
      snapshot.ParseFromString(snapshot_bytes)
      snapshot.startup_info.ParseFromString(startup_bytes)
      snapshot.timestamp = int(ts)

      res.append(snapshot)
    return res

  @utils.Synchronized
  def ReadClientStartupInfoHistory(
      self,
      client_id: str,
      timerange: Optional[
          tuple[Optional[rdfvalue.RDFDatetime], Optional[rdfvalue.RDFDatetime]]
      ] = None,
      exclude_snapshot_collections: bool = False,
  ) -> Sequence[jobs_pb2.StartupInfo]:
    """Reads the full history for a particular client."""
    # _ParseTimeRange is implemented in InMemoryDB class that uses this mixin.
    from_time, to_time = self._ParseTimeRange(timerange)  # pytype: disable=attribute-error

    history = self.startup_history.get(client_id, None)
    if not history:
      return []

    if exclude_snapshot_collections:
      snapshot_timestamps = self.clients.get(client_id, {})
      history = {
          ts: si for ts, si in history.items() if ts not in snapshot_timestamps
      }

    res = []
    for ts in sorted(history, reverse=True):
      if ts < from_time or ts > to_time:
        continue

      startup_info = jobs_pb2.StartupInfo()
      startup_info.ParseFromString(history[ts])
      startup_info.timestamp = int(ts)
      res.append(startup_info)

    return res

  @utils.Synchronized
  def MultiAddClientKeywords(
      self,
      client_ids: Collection[str],
      keywords: Collection[str],
  ) -> None:
    """Associates the provided keywords with the specified clients."""
    for client_id in client_ids:
      if client_id not in self.metadatas:
        raise db.AtLeastOneUnknownClientError(client_ids)

    for client_id in client_ids:
      for kw in keywords:
        self.keywords.setdefault(kw, {})
        self.keywords[kw][client_id] = rdfvalue.RDFDatetime.Now()

  @utils.Synchronized
  def ListClientsForKeywords(
      self,
      keywords: Collection[str],
      start_time: Optional[rdfvalue.RDFDatetime] = None,
  ) -> Mapping[str, Collection[str]]:
    """Lists the clients associated with keywords."""
    res = {kw: [] for kw in keywords}
    for kw in keywords:
      for client_id, timestamp in self.keywords.get(kw, {}).items():
        if start_time is not None and timestamp < start_time:
          continue
        res[kw].append(client_id)
    return res

  @utils.Synchronized
  def RemoveClientKeyword(
      self,
      client_id: str,
      keyword: str,
  ) -> None:
    """Removes the association of a particular client to a keyword."""
    if keyword in self.keywords and client_id in self.keywords[keyword]:
      del self.keywords[keyword][client_id]

  @utils.Synchronized
  def MultiAddClientLabels(
      self,
      client_ids: Collection[str],
      owner: str,
      labels: Collection[str],
  ) -> None:
    """Attaches user labels to the specified clients."""
    if owner not in self.users:
      raise db.UnknownGRRUserError(owner)

    for client_id in client_ids:
      if client_id not in self.metadatas:
        raise db.AtLeastOneUnknownClientError(client_ids)

    for client_id in client_ids:
      client_labels = self.labels.setdefault(client_id, dict())
      client_labels.setdefault(owner, set()).update(set(labels))

  @utils.Synchronized
  def MultiReadClientLabels(
      self,
      client_ids: Collection[str],
  ) -> Mapping[str, Sequence[objects_pb2.ClientLabel]]:
    """Reads the user labels for a list of clients."""
    res = {}
    for client_id in client_ids:
      res[client_id] = []
      owner_dict = self.labels.get(client_id, {})
      for owner, labels in owner_dict.items():
        for l in labels:
          res[client_id].append(objects_pb2.ClientLabel(owner=owner, name=l))
      res[client_id].sort(key=lambda label: (label.owner, label.name))

    return res

  @utils.Synchronized
  def RemoveClientLabels(
      self,
      client_id: str,
      owner: str,
      labels: Sequence[str],
  ) -> None:
    """Removes a list of user labels from a given client."""
    labelset = self.labels.setdefault(client_id, {}).setdefault(owner, set())
    for l in labels:
      labelset.discard(utils.SmartUnicode(l))

  @utils.Synchronized
  def ReadAllClientLabels(self) -> Collection[str]:
    """Lists all client labels known to the system."""
    results = set()
    for labels_dict in self.labels.values():
      for labels in labels_dict.values():
        results.update(labels)
    return results

  @utils.Synchronized
  def WriteClientStartupInfo(
      self,
      client_id: str,
      startup_info: jobs_pb2.StartupInfo,
  ) -> None:
    """Writes a new client startup record."""
    if client_id not in self.metadatas:
      raise db.UnknownClientError(client_id)

    ts = rdfvalue.RDFDatetime.Now()
    self.metadatas[client_id]["startup_info_timestamp"] = ts
    history = self.startup_history.setdefault(client_id, {})
    history[ts] = startup_info.SerializeToString()

  @utils.Synchronized
  def WriteClientRRGStartup(
      self,
      client_id: str,
      startup: rrg_startup_pb2.Startup,
  ) -> None:
    """Writes a new RRG startup entry to the database."""
    if client_id not in self.metadatas:
      raise db.UnknownClientError(client_id)

    # We want to store a copy as messages are mutable and we don't want anyone
    # to be able to mutate anything that is stored in the database.
    startup_copy = rrg_startup_pb2.Startup()
    startup_copy.CopyFrom(startup)

    self.rrg_startups[client_id].append(startup_copy)

  @utils.Synchronized
  def ReadClientRRGStartup(
      self,
      client_id: str,
  ) -> Optional[rrg_startup_pb2.Startup]:
    """Reads the latest RRG startup entry for the given client."""
    if client_id not in self.metadatas:
      raise db.UnknownClientError(client_id)

    try:
      return self.rrg_startups[client_id][-1]
    except IndexError:
      return None

  @utils.Synchronized
  def ReadClientStartupInfo(
      self,
      client_id: str,
  ) -> Optional[jobs_pb2.StartupInfo]:
    """Reads the latest client startup record for a single client."""
    history = self.startup_history.get(client_id, None)
    if not history:
      return None

    ts = max(history)
    res = jobs_pb2.StartupInfo()
    res.ParseFromString(history[ts])
    res.timestamp = int(ts)

    return res

  @utils.Synchronized
  def WriteClientCrashInfo(
      self,
      client_id: str,
      crash_info: jobs_pb2.ClientCrash,
  ) -> None:
    """Writes a new client crash record."""
    if client_id not in self.metadatas:
      raise db.UnknownClientError(client_id)

    ts = rdfvalue.RDFDatetime.Now()
    self.metadatas[client_id]["last_crash_timestamp"] = ts
    history = self.crash_history.setdefault(client_id, {})
    history[ts] = crash_info.SerializeToString()

  @utils.Synchronized
  def ReadClientCrashInfo(
      self,
      client_id: str,
  ) -> Optional[jobs_pb2.ClientCrash]:
    """Reads the latest client crash record for a single client."""
    history = self.crash_history.get(client_id, None)
    if not history:
      return None

    ts = max(history)
    res = jobs_pb2.ClientCrash()
    res.ParseFromString(history[ts])
    res.timestamp = int(ts)
    return res

  @utils.Synchronized
  def ReadClientCrashInfoHistory(
      self,
      client_id: str,
  ) -> Sequence[jobs_pb2.ClientCrash]:
    """Reads the full crash history for a particular client."""
    history = self.crash_history.get(client_id)
    if not history:
      return []
    res = []
    for ts in sorted(history, reverse=True):
      client_data = jobs_pb2.ClientCrash()
      client_data.ParseFromString(history[ts])
      client_data.timestamp = int(ts)
      res.append(client_data)
    return res

  @utils.Synchronized
  def DeleteClient(
      self,
      client_id: str,
  ) -> None:
    """Deletes a client with all associated metadata."""
    try:
      del self.metadatas[client_id]
    except KeyError:
      raise db.UnknownClientError(client_id)

    self.clients.pop(client_id, None)

    self.labels.pop(client_id, None)

    self.startup_history.pop(client_id, None)

    self.crash_history.pop(client_id, None)

    for key in [k for k in self.flows if k[0] == client_id]:
      self.flows.pop(key)
    for key in [k for k in self.flow_requests if k[0] == client_id]:
      self.flow_requests.pop(key)
    for key in [k for k in self.flow_processing_requests if k[0] == client_id]:
      self.flow_processing_requests.pop(key)

    for kw in self.keywords:
      self.keywords[kw].pop(client_id, None)
