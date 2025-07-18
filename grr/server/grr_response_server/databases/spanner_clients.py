#!/usr/bin/env python
"""A module with client methods of the Spanner database implementation."""

import datetime
import logging
import re
from typing import Collection, Iterator, Mapping, Optional, Sequence, Tuple

from google.api_core.exceptions import NotFound
from google.cloud import spanner as spanner_lib

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.util import iterator
from grr_response_proto import jobs_pb2
from grr_response_proto import objects_pb2
# Aliasing the import since the name db clashes with the db annotation.
from grr_response_server.databases import db as db_lib
from grr_response_server.databases import db_utils
from grr_response_server.databases import spanner_utils
from grr_response_server.models import clients as models_clients
from grr_response_proto.rrg import startup_pb2 as rrg_startup_pb2


class ClientsMixin:
  """A Spanner database mixin with implementation of client methods."""

  db: spanner_utils.Database

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def MultiWriteClientMetadata(
      self,
      client_ids: Collection[str],
      first_seen: Optional[rdfvalue.RDFDatetime] = None,
      last_ping: Optional[rdfvalue.RDFDatetime] = None,
      last_foreman: Optional[rdfvalue.RDFDatetime] = None,
      fleetspeak_validation_info: Optional[Mapping[str, str]] = None,
  ) -> None:
    """Writes metadata about the clients."""
    if not client_ids:
      return

    row = {}

    if first_seen is not None:
      row["FirstSeenTime"] = first_seen.AsDatetime()
    if last_ping is not None:
      row["LastPingTime"] = last_ping.AsDatetime()
    if last_foreman is not None:
      row["LastForemanTime"] = last_foreman.AsDatetime()

    if fleetspeak_validation_info is not None:
      if fleetspeak_validation_info:
        row["FleetspeakValidationInfo"] = (
            models_clients.FleetspeakValidationInfoFromDict(
                fleetspeak_validation_info
            )
        )
      else:
        row["FleetspeakValidationInfo"] = None

    def Mutation(mut) -> None:
      columns = []
      rows = []
      for client_id in client_ids:
        client_row = {"ClientId": client_id, **row}
        columns, values = zip(*client_row.items())
        rows.append(values)
      mut.insert_or_update(table="Clients", columns=columns, values=rows)

    self.db.Mutate(Mutation, txn_tag="MultiWriteClientMetadata")

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def MultiReadClientMetadata(
      self,
      client_ids: Collection[str],
  ) -> Mapping[str, objects_pb2.ClientMetadata]:
    """Reads ClientMetadata records for a list of clients."""
    result = {}

    keys = []
    for client_id in client_ids:
      keys.append([client_id])
    keyset = spanner_lib.KeySet(keys=keys)

    cols = (
        "ClientId",
        "LastStartupTime",
        "LastCrashTime",
        "Certificate",
        "FirstSeenTime",
        "LastPingTime",
        "LastForemanTime",
        "FleetspeakValidationInfo",
    )

    for row in self.db.ReadSet(table="Clients",
                               rows=keyset,
                               cols=cols,
                               txn_tag="MultiReadClientMetadata"):
      client_id = row[0]

      metadata = objects_pb2.ClientMetadata()

      if row[1] is not None:
        metadata.startup_info_timestamp = int(
            rdfvalue.RDFDatetime.FromDatetime(row[1])
        )
      if row[2] is not None:
        metadata.last_crash_timestamp = int(
            rdfvalue.RDFDatetime.FromDatetime(row[2])
        )
      if row[3] is not None:
        metadata.certificate = row[3]
      if row[4] is not None:
        metadata.first_seen = int(
            rdfvalue.RDFDatetime.FromDatetime(row[4])
        )
      if row[5] is not None:
        metadata.ping = int(
            rdfvalue.RDFDatetime.FromDatetime(row[5])
        )
      if row[6] is not None:
        metadata.last_foreman_time = int(
            rdfvalue.RDFDatetime.FromDatetime(row[6])
        )
      if row[7] is not None:
        metadata.last_fleetspeak_validation_info.ParseFromString(
            row[7]
        )

      result[client_id] = metadata

    return result

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def MultiAddClientLabels(
      self,
      client_ids: Collection[str],
      owner: str,
      labels: Collection[str],
  ) -> None:
    """Attaches user labels to the specified clients."""
    # Early return to avoid generating empty mutation.
    if not client_ids or not labels:
      return

    def Mutation(mut) -> None:
      label_rows = []
      for label in labels:
        label_rows.append([label])
      mut.insert_or_update(table="Labels", columns=["Label"], values=label_rows)

      client_rows = []
      for client_id in client_ids:
        for label in labels:
          client_rows.append([client_id, owner, label])
      columns = ["ClientId", "Owner", "Label"]
      mut.insert_or_update(table="ClientLabels", columns=columns, values=client_rows)

    try:
      self.db.Mutate(Mutation, txn_tag="MultiAddClientLabels")
    except Exception as error:
      message = str(error)
      if "Parent row for row [" in message:
        raise db_lib.AtLeastOneUnknownClientError(client_ids) from error
      elif "fk_client_label_owner_username" in message:
        raise db_lib.UnknownGRRUserError(username=owner, cause=error)
      else:
        raise

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def MultiReadClientLabels(
      self,
      client_ids: Collection[str],
  ) -> Mapping[str, Collection[objects_pb2.ClientLabel]]:
    """Reads the user labels for a list of clients."""
    result = {client_id: [] for client_id in client_ids}

    query = """
    SELECT l.ClientId, ARRAY_AGG((l.Owner, l.Label))
      FROM ClientLabels AS l
     WHERE l.ClientId IN UNNEST({client_ids})
     GROUP BY l.ClientId
    """
    params = {"client_ids": client_ids}

    for client_id, labels in self.db.ParamQuery(
        query, params, txn_tag="MultiReadClientLabels"
    ):
      for owner, label in labels:
        label_proto = objects_pb2.ClientLabel()
        label_proto.name = label
        label_proto.owner = owner
        result[client_id].append(label_proto)

    for labels in result.values():
      labels.sort(key=lambda label: (label.owner, label.name))

    return result

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def RemoveClientLabels(
      self,
      client_id: str,
      owner: str,
      labels: Collection[str],
  ) -> None:
    """Removes a list of user labels from a given client."""

    def Mutation(mut) -> None:
      keys = []
      for label in labels:
        keys.append([client_id, owner, label])
      mut.delete(table="ClientLabels", keyset=spanner_lib.KeySet(keys=keys))

    self.db.Mutate(Mutation, txn_tag="RemoveClientLabels")

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadAllClientLabels(self) -> Collection[str]:
    """Lists all client labels known to the system."""
    result = []

    query = """
    SELECT l.Label
      FROM Labels AS l
    """

    for (label,) in self.db.Query(query, txn_tag="ReadAllClientLabels"):
      result.append(label)

    return result

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def WriteClientSnapshot(self, snapshot: objects_pb2.ClientSnapshot) -> None:
    """Writes new client snapshot."""

    startup = snapshot.startup_info
    snapshot_without_startup_info = objects_pb2.ClientSnapshot()
    snapshot_without_startup_info.CopyFrom(snapshot)
    snapshot_without_startup_info.ClearField("startup_info")

    def Mutation(mut) -> None:
      clients_rows = []
      clients_rows.append([snapshot.client_id,spanner_lib.COMMIT_TIMESTAMP,spanner_lib.COMMIT_TIMESTAMP])
      clients_columns = ["ClientId", "LastSnapshotTime", "LastStartupTime"]
      mut.update(table="Clients", columns=clients_columns, values=clients_rows)

      snapshots_rows = []
      snapshots_rows.append([snapshot.client_id, spanner_lib.COMMIT_TIMESTAMP, snapshot_without_startup_info])
      snapshots_columns= ["ClientId", "CreationTime", "Snapshot"]
      mut.insert(table="ClientSnapshots", columns=snapshots_columns, values=snapshots_rows)

      startups_rows = []
      startups_rows.append([snapshot.client_id, spanner_lib.COMMIT_TIMESTAMP, startup])
      startups_columns = [ "ClientId", "CreationTime", "Startup"]
      mut.insert(table="ClientStartups", columns=startups_columns, values=startups_rows)

    try:
      self.db.Mutate(Mutation, txn_tag="WriteClientSnapshot")
    except NotFound as error:
      raise db_lib.UnknownClientError(snapshot.client_id, cause=error)

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def MultiReadClientSnapshot(
      self,
      client_ids: Collection[str],
  ) -> Mapping[str, Optional[objects_pb2.ClientSnapshot]]:
    """Reads the latest client snapshots for a list of clients."""
    if not client_ids:
      return {}

    result = {client_id: None for client_id in client_ids}

    query = """
    SELECT c.ClientId, ss.CreationTime, ss.Snapshot, su.Startup
      FROM Clients AS c, ClientSnapshots AS ss, ClientStartups AS su
     WHERE c.ClientId IN UNNEST({client_ids})
       AND ss.ClientId = c.ClientId
       AND ss.CreationTime = c.LastSnapshotTime
       AND su.ClientId = c.ClientId
       AND su.CreationTime = c.LastStartupTime
    """
    for row in self.db.ParamQuery(
        query, {"client_ids": client_ids}, txn_tag="MultiReadClientSnapshot"
    ):
      client_id, creation_time, snapshot_bytes, startup_bytes = row

      snapshot = objects_pb2.ClientSnapshot()
      snapshot.ParseFromString(snapshot_bytes)
      snapshot.startup_info.ParseFromString(startup_bytes)
      snapshot.timestamp = int(rdfvalue.RDFDatetime.FromDatetime(creation_time))

      result[client_id] = snapshot

    return result

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadClientSnapshotHistory(
      self,
      client_id: str,
      timerange: Optional[
          tuple[Optional[rdfvalue.RDFDatetime], Optional[rdfvalue.RDFDatetime]]
      ] = None,
  ) -> Sequence[objects_pb2.ClientSnapshot]:
    """Reads the full history for a particular client."""
    result = []

    query = """
    SELECT ss.CreationTime, ss.Snapshot, su.Startup
      FROM ClientSnapshots AS ss, ClientStartups AS su
     WHERE ss.ClientId = {client_id}
       AND ss.ClientId = su.ClientId
       AND ss.CreationTime = su.CreationTime
    """
    params = {"client_id": client_id}

    if timerange is not None:
      time_since, time_until = timerange
      if time_since is not None:
        query += " AND ss.CreationTime >= {time_since}"
        params["time_since"] = time_since.AsDatetime()
      if time_until is not None:
        query += " AND ss.CreationTime <= {time_until}"
        params["time_until"] = time_until.AsDatetime()

    query += " ORDER BY ss.CreationTime DESC"

    for row in self.db.ParamQuery(
        query, params=params, txn_tag="ReadClientSnapshotHistory"
    ):
      creation_time, snapshot_bytes, startup_bytes = row

      snapshot = objects_pb2.ClientSnapshot()
      snapshot.ParseFromString(snapshot_bytes)
      snapshot.startup_info.ParseFromString(startup_bytes)
      snapshot.timestamp = int(rdfvalue.RDFDatetime.FromDatetime(creation_time))

      result.append(snapshot)

    return result

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def WriteClientStartupInfo(
      self,
      client_id: str,
      startup: jobs_pb2.StartupInfo,
  ) -> None:
    """Writes a new client startup record."""

    def Mutation(mut: spanner_utils.Mutation) -> None:
      mut.update(table="Clients",
                 columns=["ClientId", "LastStartupTime"],
                 values=[[client_id, spanner_lib.COMMIT_TIMESTAMP]])

      mut.insert(table="ClientStartups",
                 columns=["ClientId", "CreationTime", "Startup"],
                 values=[[client_id ,spanner_lib.COMMIT_TIMESTAMP, startup]])

    try:
      self.db.Mutate(Mutation, txn_tag="WriteClientStartupInfo")
    except NotFound as error:
      raise db_lib.UnknownClientError(client_id, cause=error)

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def WriteClientRRGStartup(
      self,
      client_id: str,
      startup: rrg_startup_pb2.Startup,
  ) -> None:
    """Writes a new RRG startup entry to the database."""

    def Mutation(mut: spanner_utils.Mutation) -> None:
      mut.update(
        table="Clients",
        columns=("ClientId", "LastRRGStartupTime"),
        values=[(client_id, spanner_lib.COMMIT_TIMESTAMP)]
      )

      mut.insert(
        table="ClientRRGStartups",
        columns=("ClientId", "CreationTime", "Startup"),
        values=[(client_id, spanner_lib.COMMIT_TIMESTAMP, startup)]
      )

    try:
      self.db.Mutate(Mutation)
    except NotFound as error:
      raise db_lib.UnknownClientError(client_id, cause=error)

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadClientRRGStartup(
      self,
      client_id: str,
  ) -> Optional[rrg_startup_pb2.Startup]:
    """Reads the latest RRG startup entry for the given client."""
    query = """
    SELECT su.Startup
      FROM Clients AS c
           LEFT JOIN ClientRRGStartups AS su
                  ON c.ClientId = su.ClientId
                 AND c.LastRRGStartupTime = su.CreationTime
     WHERE c.ClientId = {client_id}
    """
    params = {
        "client_id": client_id,
    }

    try:
      (startup_bytes,) = self.db.ParamQuerySingle(
          query, params, txn_tag="ReadClientRRGStartup"
      )
    except NotFound:
      raise db_lib.UnknownClientError(client_id)  # pylint: disable=raise-missing-from

    if startup_bytes is None:
      return None

    return rrg_startup_pb2.Startup.FromString(startup_bytes)

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadClientStartupInfo(
      self,
      client_id: str,
  ) -> Optional[jobs_pb2.StartupInfo]:
    """Reads the latest client startup record for a single client."""

    query = """
    SELECT su.CreationTime, su.Startup
      FROM Clients AS c, ClientStartups AS su
     WHERE c.ClientId = {client_id}
       AND c.ClientId = su.ClientId
       AND c.LastStartupTime = su.CreationTime
    """
    params = {"client_id": client_id}

    try:
      (creation_time, startup_bytes) = self.db.ParamQuerySingle(
          query, params, txn_tag="ReadClientStartupInfo"
      )
    except NotFound:
      return None

    startup = jobs_pb2.StartupInfo()
    startup.ParseFromString(startup_bytes)
    startup.timestamp = int(rdfvalue.RDFDatetime.FromDatetime(creation_time))
    return startup

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def WriteClientCrashInfo(
      self,
      client_id: str,
      crash: jobs_pb2.ClientCrash,
  ) -> None:
    """Writes a new client crash record."""

    def Mutation(mut: spanner_utils.Mutation) -> None:
      mut.update(table="Clients",
                 columns=["ClientId", "LastCrashTime"],
                 values=[[client_id, spanner_lib.COMMIT_TIMESTAMP]])

      mut.insert(table="ClientCrashes",
                 columns=["ClientId", "CreationTime", "Crash"],
                 values=[[client_id, spanner_lib.COMMIT_TIMESTAMP, crash]])

    try:
      self.db.Mutate(Mutation, txn_tag="WriteClientCrashInfo")
    except NotFound as error:
      raise db_lib.UnknownClientError(client_id, cause=error)

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadClientCrashInfo(
      self,
      client_id: str,
  ) -> Optional[jobs_pb2.ClientCrash]:
    """Reads the latest client crash record for a single client."""

    query = """
    SELECT cr.CreationTime, cr.Crash
      FROM Clients AS c, ClientCrashes AS cr
     WHERE c.ClientId = {client_id}
       AND c.ClientId = cr.ClientId
       AND c.LastCrashTime = cr.CreationTime
    """
    params = {"client_id": client_id}

    try:
      (creation_time, crash_bytes) = self.db.ParamQuerySingle(
          query, params, txn_tag="ReadClientCrashInfo"
      )
    except NotFound:
      return None

    crash = jobs_pb2.ClientCrash()
    crash = crash.FromString(crash_bytes)
    crash.timestamp = int(rdfvalue.RDFDatetime.FromDatetime(creation_time))

    return crash

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadClientCrashInfoHistory(
      self,
      client_id: str,
  ) -> Sequence[jobs_pb2.ClientCrash]:
    """Reads the full crash history for a particular client."""
    result = []

    query = """
    SELECT cr.CreationTime, cr.Crash
      FROM ClientCrashes AS cr
     WHERE cr.ClientId = {client_id}
     ORDER BY cr.CreationTime DESC
    """
    params = {"client_id": client_id}

    for row in self.db.ParamQuery(
        query, params, txn_tag="ReadClientCrashInfoHistory"
    ):
      creation_time, crash_bytes = row

      crash = jobs_pb2.ClientCrash()
      crash.ParseFromString(crash_bytes)
      crash.timestamp = int(rdfvalue.RDFDatetime.FromDatetime(creation_time))

      result.append(crash)

    return result

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def MultiReadClientFullInfo(
      self,
      client_ids: Collection[str],
      min_last_ping: Optional[rdfvalue.RDFDatetime] = None,
  ) -> Mapping[str, objects_pb2.ClientFullInfo]:
    """Reads full client information for a list of clients."""
    if not client_ids:
      return {}

    result = {}

    query = """
    SELECT c.ClientId,
           c.Certificate,
           c.FleetspeakValidationInfo,
           c.FirstSeenTime, c.LastPingTime, c.LastForemanTime,
           c.LastSnapshotTime, c.LastStartupTime, c.LastCrashTime,
           ss_last.Snapshot,
           su_last.Startup, su_last_snapshot.Startup,
           rrg_su_last.Startup,
           ARRAY(SELECT AS STRUCT
                        l.Owner, l.Label
                   FROM ClientLabels AS l
                  WHERE l.ClientId = c.ClientId)
      FROM Clients AS c
           LEFT JOIN ClientSnapshots AS ss_last
                  ON (c.ClientId = ss_last.ClientId)
                 AND (c.LastSnapshotTime = ss_last.CreationTime)
           LEFT JOIN ClientStartups AS su_last
                  ON (c.ClientId = su_last.ClientId)
                 AND (c.LastStartupTime = su_last.CreationTime)
           LEFT JOIN ClientRrgStartups AS rrg_su_last
                  ON (c.ClientId = rrg_su_last.ClientId)
                 AND (c.LastRrgStartupTime = rrg_su_last.CreationTime)
           LEFT JOIN ClientStartups AS su_last_snapshot
                  ON (c.ClientId = su_last_snapshot.ClientId)
                 AND (c.LastSnapshotTime = su_last_snapshot.CreationTime)
     WHERE c.ClientId IN UNNEST({client_ids})
    """
    params = {"client_ids": client_ids}

    if min_last_ping is not None:
      query += " AND c.LastPingTime >= {min_last_ping_time}"
      params["min_last_ping_time"] = min_last_ping.AsDatetime()

    for row in self.db.ParamQuery(
        query, params, txn_tag="MultiReadClientFullInfo"
    ):
      client_id, certificate_bytes, *row = row
      fleetspeak_validation_info_bytes, *row = row
      first_seen_time, last_ping_time, *row = row
      last_foreman_time, *row = row
      last_snapshot_time, last_startup_time, last_crash_time, *row = row
      last_snapshot_bytes, *row = row
      last_startup_bytes, last_snapshot_startup_bytes, *row = row
      last_rrg_startup_bytes, *row = row
      (label_rows,) = row

      info = objects_pb2.ClientFullInfo()

      if last_startup_bytes is not None:
        info.last_startup_info.ParseFromString(last_startup_bytes)
        info.last_startup_info.timestamp = int(
            rdfvalue.RDFDatetime.FromDatetime(last_startup_time)
        )

      if last_snapshot_bytes is not None:
        info.last_snapshot.ParseFromString(last_snapshot_bytes)
        info.last_snapshot.timestamp = int(
            rdfvalue.RDFDatetime.FromDatetime(last_snapshot_time)
        )

        if last_snapshot_startup_bytes is not None:
          info.last_snapshot.startup_info.ParseFromString(
              last_snapshot_startup_bytes
          )
          info.last_snapshot.startup_info.timestamp = int(
              rdfvalue.RDFDatetime.FromDatetime(last_snapshot_time)
          )

      if certificate_bytes is not None:
        info.metadata.certificate = certificate_bytes
      if fleetspeak_validation_info_bytes is not None:
        info.metadata.last_fleetspeak_validation_info.ParseFromString(
            fleetspeak_validation_info_bytes
        )
      if first_seen_time is not None:
        info.metadata.first_seen = int(
            rdfvalue.RDFDatetime.FromDatetime(first_seen_time)
        )
      if last_ping_time is not None:
        info.metadata.ping = int(
            rdfvalue.RDFDatetime.FromDatetime(last_ping_time)
        )
      if last_foreman_time is not None:
        info.metadata.last_foreman_time = int(
            rdfvalue.RDFDatetime.FromDatetime(last_foreman_time)
        )
      if last_startup_time is not None:
        info.metadata.startup_info_timestamp = int(
            rdfvalue.RDFDatetime.FromDatetime(last_startup_time)
        )
      if last_crash_time is not None:
        info.metadata.last_crash_timestamp = int(
            rdfvalue.RDFDatetime.FromDatetime(last_crash_time)
        )

      info.last_snapshot.client_id = client_id

      for owner, label in label_rows:
        info.labels.add(owner=owner, name=label)

      if last_rrg_startup_bytes is not None:
        info.last_rrg_startup.ParseFromString(last_rrg_startup_bytes)

      result[client_id] = info

    return result

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadClientLastPings(
      self,
      min_last_ping: Optional[rdfvalue.RDFDatetime] = None,
      max_last_ping: Optional[rdfvalue.RDFDatetime] = None,
      batch_size: int = 0,
  ) -> Iterator[Mapping[str, Optional[rdfvalue.RDFDatetime]]]:
    """Yields dicts of last-ping timestamps for clients in the DB."""
    if not batch_size:
      batch_size = db_lib.CLIENT_IDS_BATCH_SIZE

    last_client_id = "0"

    while True:
      client_last_pings_batch = self._ReadClientLastPingsBatch(
          count=(batch_size or db_lib.CLIENT_IDS_BATCH_SIZE),
          last_client_id=last_client_id,
          min_last_ping_time=min_last_ping,
          max_last_ping_time=max_last_ping,
      )

      if client_last_pings_batch:
        yield client_last_pings_batch
      if len(client_last_pings_batch) < batch_size:
        break

      last_client_id = max(client_last_pings_batch.keys())

  def _ReadClientLastPingsBatch(
      self,
      count: int,
      last_client_id: str,
      min_last_ping_time: Optional[rdfvalue.RDFDatetime],
      max_last_ping_time: Optional[rdfvalue.RDFDatetime],
  ) -> Mapping[str, Optional[rdfvalue.RDFDatetime]]:
    """Reads a single batch of last client last ping times.

    Args:
      count: The number of entries to read in the batch.
      last_client_id: The identifier of the last client of the previous batch.
      min_last_ping_time: An (optional) lower bound on the last ping time value.
      max_last_ping_time: An (optional) upper bound on the last ping time value.

    Returns:
      A mapping from client identifiers to client last ping times.
    """
    result = {}

    query = """
    SELECT c.ClientId, c.LastPingTime
      FROM Clients AS c
     WHERE c.ClientId > {last_client_id}
    """
    params = {"last_client_id": last_client_id}

    if min_last_ping_time is not None:
      query += " AND c.LastPingTime >= {min_last_ping_time}"
      params["min_last_ping_time"] = min_last_ping_time.AsDatetime()
    if max_last_ping_time is not None:
      query += (
          " AND (c.LastPingTime IS NULL OR "
          "      c.LastPingTime <= {max_last_ping_time})"
      )
      params["max_last_ping_time"] = max_last_ping_time.AsDatetime()

    query += """
    ORDER BY ClientId
    LIMIT {count}
    """
    params["count"] = count

    for client_id, last_ping_time in self.db.ParamQuery(
        query, params, txn_tag="ReadClientLastPingsBatch"
    ):

      if last_ping_time is not None:
        result[client_id] = rdfvalue.RDFDatetime.FromDatetime(last_ping_time)
      else:
        result[client_id] = None

    return result

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def DeleteClient(self, client_id: str) -> None:
    """Deletes a client with all associated metadata."""

    def Transaction(txn) -> None:
      # It looks like Spanner does not raise exception if we attempt to delete
      # a non-existing row, so we have to verify row existence ourself.
      keyrange = spanner_lib.KeyRange(start_closed=[client_id], end_closed=[client_id])
      keyset = spanner_lib.KeySet(ranges=[keyrange])
      try:
        txn.read(table="Clients", keyset=keyset, columns=["ClientId"]).one()
      except NotFound as error:
        raise db_lib.UnknownClientError(client_id, cause=error)

      txn.delete(table="Clients", keyset=keyset)

    self.db.Transact(Transaction, txn_tag="DeleteClient")

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def MultiAddClientKeywords(
      self,
      client_ids: Collection[str],
      keywords: Collection[str],
  ) -> None:
    """Associates the provided keywords with the specified clients."""
    # Early return to avoid generating empty mutation.
    if not client_ids or not keywords:
      return

    def Mutation(mut: spanner_utils.Mutation) -> None:
      for client_id in client_ids:
        rows = []
        for keyword in keywords:
          row = [client_id, keyword, spanner_lib.COMMIT_TIMESTAMP]
          rows.append(row)
        columns = ["ClientId", "Keyword", "CreationTime"]
        mut.insert_or_update(table="ClientKeywords", columns=columns, values=rows)

    try:
      self.db.Mutate(Mutation, txn_tag="MultiAddClientKeywords")
    except NotFound as error:
      raise db_lib.AtLeastOneUnknownClientError(client_ids) from error

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ListClientsForKeywords(
      self,
      keywords: Collection[str],
      start_time: Optional[rdfvalue.RDFDatetime] = None,
  ) -> Mapping[str, Collection[str]]:
    """Lists the clients associated with keywords."""
    results = {keyword: [] for keyword in keywords}

    query = """
    SELECT k.Keyword, ARRAY_AGG(k.ClientId)
      FROM ClientKeywords@{{FORCE_INDEX=ClientKeywordsByKeywordCreationTime}} AS k
     WHERE k.Keyword IN UNNEST({keywords})
    """
    params = {
        "keywords": list(keywords),
    }

    if start_time is not None:
      query += " AND k.CreationTime >= {cutoff_time}"
      params["cutoff_time"] = start_time.AsDatetime()

    query += " GROUP BY k.Keyword"

    for keyword, client_ids in self.db.ParamQuery(
        query, params, txn_tag="ListClientsForKeywords"
    ):
      results[keyword].extend(client_ids)

    return results

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def RemoveClientKeyword(self, client_id: str, keyword: str) -> None:
    """Removes the association of a particular client to a keyword."""
    self.db.Delete(
        table="ClientKeywords",
        key=(client_id, keyword),
        txn_tag="RemoveClientKeyword",
    )


_EPOCH = datetime.datetime.fromtimestamp(0, datetime.timezone.utc)

_DELETE_BATCH_SIZE = 5_000
