#!/usr/bin/env python
"""The MySQL database methods for client handling."""

from collections.abc import Collection, Iterator, Mapping, Sequence
import itertools
from typing import Optional

import MySQLdb
from MySQLdb.constants import ER as mysql_error_constants
import MySQLdb.cursors

from grr_response_core.lib import rdfvalue
from grr_response_proto import jobs_pb2
from grr_response_proto import objects_pb2
from grr_response_server.databases import db
from grr_response_server.databases import db_utils
from grr_response_server.databases import mysql_utils
from grr_response_server.models import clients as models_clients
from grr_response_proto.rrg import startup_pb2 as rrg_startup_pb2


class MySQLDBClientMixin(object):
  """MySQLDataStore mixin for client related functions."""

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction()
  def MultiWriteClientMetadata(
      self,
      client_ids: Collection[str],
      first_seen: Optional[rdfvalue.RDFDatetime] = None,
      last_ping: Optional[rdfvalue.RDFDatetime] = None,
      last_foreman: Optional[rdfvalue.RDFDatetime] = None,
      fleetspeak_validation_info: Optional[Mapping[str, str]] = None,
      cursor: Optional[MySQLdb.cursors.Cursor] = None,
  ) -> None:
    """Writes metadata about the clients."""
    assert cursor is not None
    # Early return to avoid generating empty query.
    if not client_ids:
      return

    common_placeholders = []
    values = dict()
    column_names = ["client_id"]

    for i, client_id in enumerate(client_ids):
      values[f"client_id{i}"] = db_utils.ClientIDToInt(client_id)

    if first_seen is not None:
      column_names.append("first_seen")
      common_placeholders.append("FROM_UNIXTIME(%(first_seen)s)")
      values["first_seen"] = mysql_utils.RDFDatetimeToTimestamp(first_seen)
    if last_ping is not None:
      column_names.append("last_ping")
      common_placeholders.append("FROM_UNIXTIME(%(last_ping)s)")
      values["last_ping"] = mysql_utils.RDFDatetimeToTimestamp(last_ping)
    if last_foreman is not None:
      column_names.append("last_foreman")
      common_placeholders.append("FROM_UNIXTIME(%(last_foreman)s)")
      values["last_foreman"] = mysql_utils.RDFDatetimeToTimestamp(last_foreman)

    if fleetspeak_validation_info is not None:
      column_names.append("last_fleetspeak_validation_info")
      common_placeholders.append("%(last_fleetspeak_validation_info)s")
      if fleetspeak_validation_info:
        pb = models_clients.FleetspeakValidationInfoFromDict(
            fleetspeak_validation_info
        )
        values["last_fleetspeak_validation_info"] = pb.SerializeToString()
      else:
        # Write null for empty or non-existent validation info.
        values["last_fleetspeak_validation_info"] = None

    # For each client_id, we create a row tuple with a numbered client id
    # placeholder followed by common placeholder values for the columns being
    # updated. Example query string:
    # INSERT INTO clients
    # VALUES (%(client_id0)s, %(last_ping)s), (%(client_id1)s, %(last_ping)s)
    # ON DUPLICATE KEY UPDATE
    # client_id = VALUES(client_id)
    row_tuples = []
    for i, client_id in enumerate(client_ids):
      row_placeholders = ", ".join([f"%(client_id{i})s"] + common_placeholders)
      row_tuples.append(f"({row_placeholders})")

    column_updates = [f"{column} = VALUES({column})" for column in column_names]

    cursor.execute(
        f"""
    INSERT INTO clients ({', '.join(column_names)})
    VALUES {', '.join(row_tuples)}
    ON DUPLICATE KEY UPDATE {', '.join(column_updates)}
    """,
        values,
    )

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction(readonly=True)
  def MultiReadClientMetadata(
      self,
      client_ids: Collection[str],
      cursor: Optional[MySQLdb.cursors.Cursor] = None,
  ) -> Mapping[str, objects_pb2.ClientMetadata]:
    """Reads ClientMetadata records for a list of clients."""
    assert cursor is not None
    ids = [db_utils.ClientIDToInt(client_id) for client_id in client_ids]
    query = """
      SELECT
        client_id,
        certificate,
        UNIX_TIMESTAMP(last_ping),
        UNIX_TIMESTAMP(last_foreman),
        UNIX_TIMESTAMP(first_seen),
        UNIX_TIMESTAMP(last_crash_timestamp),
        UNIX_TIMESTAMP(last_startup_timestamp),
        last_fleetspeak_validation_info
      FROM
        clients
      WHERE
        client_id IN ({})""".format(", ".join(["%s"] * len(ids)))
    ret = {}
    cursor.execute(query, ids)
    while True:
      row = cursor.fetchone()
      if not row:
        break
      cid, crt, ping, foreman, first, lct, lst, fsvi = row

      metadata = objects_pb2.ClientMetadata()
      if crt is not None:
        metadata.certificate = crt
      if first is not None:
        metadata.first_seen = int(mysql_utils.TimestampToRDFDatetime(first))
      if ping is not None:
        metadata.ping = int(mysql_utils.TimestampToRDFDatetime(ping))
      if foreman is not None:
        metadata.last_foreman_time = int(
            mysql_utils.TimestampToRDFDatetime(foreman)
        )
      if lst is not None:
        metadata.startup_info_timestamp = int(
            mysql_utils.TimestampToRDFDatetime(lst)
        )
      if lct is not None:
        metadata.last_crash_timestamp = int(
            mysql_utils.TimestampToRDFDatetime(lct)
        )
      if fsvi is not None:
        metadata.last_fleetspeak_validation_info.ParseFromString(fsvi)

      ret[db_utils.IntToClientID(cid)] = metadata

    return ret

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction()
  def WriteClientSnapshot(
      self,
      snapshot: objects_pb2.ClientSnapshot,
      cursor: Optional[MySQLdb.cursors.Cursor] = None,
  ) -> None:
    """Write new client snapshot."""
    assert cursor is not None
    cursor.execute("SET @now = NOW(6)")

    insert_history_query = (
        "INSERT INTO client_snapshot_history(client_id, timestamp, "
        "client_snapshot) VALUES (%s, @now, %s)"
    )
    insert_startup_query = (
        "INSERT INTO client_startup_history(client_id, timestamp, "
        "startup_info) VALUES(%s, @now, %s)"
    )

    client_info = {
        "last_platform": snapshot.knowledge_base.os,
    }
    update_clauses = [
        "last_snapshot_timestamp = @now",
        "last_startup_timestamp = @now",
        "last_platform = %(last_platform)s",
    ]

    update_query = (
        "UPDATE clients SET {} WHERE client_id = %(client_id)s".format(
            ", ".join(update_clauses)
        )
    )

    int_client_id = db_utils.ClientIDToInt(snapshot.client_id)
    client_info["client_id"] = int_client_id

    startup_info = jobs_pb2.StartupInfo()
    startup_info.CopyFrom(snapshot.startup_info)

    snapshot_without_startup_info = objects_pb2.ClientSnapshot()
    snapshot_without_startup_info.CopyFrom(snapshot)
    snapshot_without_startup_info.ClearField("startup_info")

    try:
      cursor.execute(
          insert_history_query,
          (int_client_id, snapshot_without_startup_info.SerializeToString()),
      )
      cursor.execute(
          insert_startup_query,
          (int_client_id, startup_info.SerializeToString()),
      )
      cursor.execute(update_query, client_info)
    except MySQLdb.IntegrityError as e:
      if e.args and e.args[0] == mysql_error_constants.NO_REFERENCED_ROW_2:
        raise db.UnknownClientError(snapshot.client_id, cause=e)
      else:
        raise

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction(readonly=True)
  def MultiReadClientSnapshot(
      self,
      client_ids: Collection[str],
      cursor: Optional[MySQLdb.cursors.Cursor] = None,
  ) -> Mapping[str, Optional[objects_pb2.ClientSnapshot]]:
    """Reads the latest client snapshots for a list of clients."""
    assert cursor is not None
    if not client_ids:
      return {}

    int_ids = [db_utils.ClientIDToInt(cid) for cid in client_ids]
    query = (
        "SELECT h.client_id, h.client_snapshot, UNIX_TIMESTAMP(h.timestamp),"
        "       s.startup_info "
        "FROM clients as c FORCE INDEX (PRIMARY), "
        "client_snapshot_history as h FORCE INDEX (PRIMARY), "
        "client_startup_history as s FORCE INDEX (PRIMARY) "
        "WHERE h.client_id = c.client_id "
        "AND s.client_id = c.client_id "
        "AND h.timestamp = c.last_snapshot_timestamp "
        "AND s.timestamp = c.last_startup_timestamp "
        "AND c.client_id IN ({})"
    ).format(", ".join(["%s"] * len(client_ids)))
    ret = {cid: None for cid in client_ids}
    cursor.execute(query, int_ids)

    while True:
      row = cursor.fetchone()
      if not row:
        break

      int_client_id, snapshot_bytes, timestamp, startup_bytes = row
      client_id = db_utils.IntToClientID(int_client_id)

      if snapshot_bytes is None:
        continue

      snapshot = objects_pb2.ClientSnapshot()
      snapshot.ParseFromString(snapshot_bytes)

      if startup_bytes is not None:
        snapshot.startup_info.ParseFromString(startup_bytes)

      snapshot.timestamp = mysql_utils.TimestampToMicrosecondsSinceEpoch(
          timestamp
      )

      ret[client_id] = snapshot
    return ret

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction(readonly=True)
  def ReadClientSnapshotHistory(
      self,
      client_id: str,
      timerange: Optional[
          tuple[Optional[rdfvalue.RDFDatetime], Optional[rdfvalue.RDFDatetime]]
      ] = None,
      cursor: Optional[MySQLdb.cursors.Cursor] = None,
  ) -> Sequence[objects_pb2.ClientSnapshot]:
    """Reads the full history for a particular client."""
    assert cursor is not None

    client_id_int = db_utils.ClientIDToInt(client_id)

    query = (
        "SELECT sn.client_snapshot, st.startup_info, "
        "       UNIX_TIMESTAMP(sn.timestamp) FROM "
        "client_snapshot_history AS sn, "
        "client_startup_history AS st WHERE "
        "sn.client_id = st.client_id AND "
        "sn.timestamp = st.timestamp AND "
        "sn.client_id=%s "
    )

    args = [client_id_int]
    if timerange:
      time_from, time_to = timerange  # pylint: disable=unpacking-non-sequence

      if time_from is not None:
        query += "AND sn.timestamp >= FROM_UNIXTIME(%s) "
        args.append(mysql_utils.RDFDatetimeToTimestamp(time_from))

      if time_to is not None:
        query += "AND sn.timestamp <= FROM_UNIXTIME(%s) "
        args.append(mysql_utils.RDFDatetimeToTimestamp(time_to))

    query += "ORDER BY sn.timestamp DESC"

    ret = []
    cursor.execute(query, args)
    for snapshot_bytes, startup_bytes, timestamp in cursor.fetchall():
      snapshot = objects_pb2.ClientSnapshot()
      snapshot.ParseFromString(snapshot_bytes)
      snapshot.startup_info.ParseFromString(startup_bytes)
      snapshot.timestamp = mysql_utils.TimestampToMicrosecondsSinceEpoch(
          timestamp
      )

      ret.append(snapshot)
    return ret

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction()
  def WriteClientStartupInfo(
      self,
      client_id: str,
      startup_info: jobs_pb2.StartupInfo,
      cursor: Optional[MySQLdb.cursors.Cursor] = None,
  ) -> None:
    """Writes a new client startup record."""
    assert cursor is not None
    cursor.execute("SET @now = NOW(6)")

    params = {
        "client_id": db_utils.ClientIDToInt(client_id),
        "startup_info": startup_info.SerializeToString(),
    }

    try:
      cursor.execute(
          """
      INSERT INTO client_startup_history
        (client_id, timestamp, startup_info)
      VALUES
        (%(client_id)s, @now, %(startup_info)s)
          """,
          params,
      )

      cursor.execute(
          """
      UPDATE clients
         SET last_startup_timestamp = @now
       WHERE client_id = %(client_id)s
      """,
          params,
      )
    except MySQLdb.IntegrityError as e:
      raise db.UnknownClientError(client_id, cause=e)

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction()
  def WriteClientRRGStartup(
      self,
      client_id: str,
      startup: rrg_startup_pb2.Startup,
      cursor: Optional[MySQLdb.cursors.Cursor] = None,
  ) -> None:
    """Writes a new RRG startup entry to the database."""
    assert cursor is not None
    query = """
    INSERT
      INTO client_rrg_startup_history (client_id, timestamp, startup)
    VALUES (%(client_id)s, NOW(6), %(startup)s)
    """
    params = {
        "client_id": db_utils.ClientIDToInt(client_id),
        "startup": startup.SerializeToString(),
    }

    try:
      cursor.execute(query, params)
    except MySQLdb.IntegrityError as error:
      raise db.UnknownClientError(client_id) from error

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction()
  def ReadClientRRGStartup(
      self,
      client_id: str,
      cursor: Optional[MySQLdb.cursors.Cursor] = None,
  ) -> Optional[rrg_startup_pb2.Startup]:
    """Reads the latest RRG startup entry for the given client."""
    assert cursor is not None
    query = """
    SELECT su.startup
      FROM clients
           LEFT JOIN (SELECT startup
                        FROM client_rrg_startup_history
                       WHERE client_id = %(client_id)s
                    ORDER BY timestamp DESC
                       LIMIT 1) AS su
                     ON TRUE
     WHERE client_id = %(client_id)s
    """
    params = {
        "client_id": db_utils.ClientIDToInt(client_id),
    }

    cursor.execute(query, params)

    row = cursor.fetchone()
    if row is None:
      raise db.UnknownClientError(client_id)

    (startup_bytes,) = row
    if startup_bytes is None:
      return None

    return rrg_startup_pb2.Startup.FromString(startup_bytes)

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction(readonly=True)
  def ReadClientStartupInfo(
      self,
      client_id: str,
      cursor: Optional[MySQLdb.cursors.Cursor] = None,
  ) -> Optional[jobs_pb2.StartupInfo]:
    """Reads the latest client startup record for a single client."""
    assert cursor is not None
    query = """
    SELECT startup_info, UNIX_TIMESTAMP(timestamp)
      FROM clients, client_startup_history
     WHERE clients.last_startup_timestamp = client_startup_history.timestamp
       AND clients.client_id = client_startup_history.client_id
       AND clients.client_id = %(client_id)s
    """
    params = {
        "client_id": db_utils.ClientIDToInt(client_id),
    }
    cursor.execute(query, params)

    row = cursor.fetchone()
    if row is None:
      return None

    startup_info, timestamp = row
    res = jobs_pb2.StartupInfo()
    res.ParseFromString(startup_info)
    res.timestamp = int(mysql_utils.TimestampToRDFDatetime(timestamp))
    return res

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction(readonly=True)
  def ReadClientStartupInfoHistory(
      self,
      client_id: str,
      timerange: Optional[
          tuple[Optional[rdfvalue.RDFDatetime], Optional[rdfvalue.RDFDatetime]]
      ] = None,
      exclude_snapshot_collections: bool = False,
      cursor: Optional[MySQLdb.cursors.Cursor] = None,
  ) -> Sequence[jobs_pb2.StartupInfo]:
    """Reads the full history for a particular client."""
    assert cursor is not None

    client_id_int = db_utils.ClientIDToInt(client_id)

    query = """
    SELECT startup_info, UNIX_TIMESTAMP(timestamp)
      FROM client_startup_history
     WHERE
        client_id = %(client_id)s
    """

    args = {"client_id": client_id_int}
    if exclude_snapshot_collections:
      query += """
       AND timestamp NOT IN (
          SELECT sn.timestamp
          FROM client_snapshot_history AS sn
          WHERE sn.client_id = %(client_id)s
      )
      """

    if timerange:
      time_from, time_to = timerange  # pylint: disable=unpacking-non-sequence

      if time_from is not None:
        query += "AND timestamp >= FROM_UNIXTIME(%(time_from)s) "
        args["time_from"] = mysql_utils.RDFDatetimeToTimestamp(time_from)

      if time_to is not None:
        query += "AND timestamp <= FROM_UNIXTIME(%(time_to)s) "
        args["time_to"] = mysql_utils.RDFDatetimeToTimestamp(time_to)

    query += "ORDER BY timestamp DESC"

    ret = []
    cursor.execute(query, args)
    for startup_bytes, timestamp in cursor.fetchall():
      startup_info = jobs_pb2.StartupInfo()
      startup_info.ParseFromString(startup_bytes)
      startup_info.timestamp = mysql_utils.TimestampToMicrosecondsSinceEpoch(
          timestamp
      )
      ret.append(startup_info)
    return ret

  def _ResponseToClientsFullInfo(self, response):
    """Creates a ClientFullInfo object from a database response."""
    if not response:
      return

    prev_cid = None
    c_full_info = objects_pb2.ClientFullInfo()
    for row in response:
      (
          cid,
          crt,
          ping,
          foreman,
          first,
          last_client_ts,
          last_crash_ts,
          last_startup_ts,
          client_obj,
          client_startup_obj,
          last_startup_obj,
          last_rrg_startup_obj,
          label_owner,
          label_name,
      ) = row

      if cid != prev_cid:
        if prev_cid is not None:
          yield db_utils.IntToClientID(prev_cid), c_full_info
          c_full_info = objects_pb2.ClientFullInfo()

        if crt is not None:
          c_full_info.metadata.certificate = crt
        if first is not None:
          c_full_info.metadata.first_seen = int(
              mysql_utils.TimestampToRDFDatetime(first)
          )
        if ping is not None:
          c_full_info.metadata.ping = int(
              mysql_utils.TimestampToRDFDatetime(ping)
          )
        if foreman is not None:
          c_full_info.metadata.last_foreman_time = int(
              mysql_utils.TimestampToRDFDatetime(foreman)
          )
        if last_startup_ts is not None:
          c_full_info.metadata.startup_info_timestamp = int(
              mysql_utils.TimestampToRDFDatetime(last_startup_ts)
          )
        if last_crash_ts is not None:
          c_full_info.metadata.last_crash_timestamp = int(
              mysql_utils.TimestampToRDFDatetime(last_crash_ts)
          )

        if client_obj is not None:
          c_full_info.last_snapshot.ParseFromString(client_obj)
          c_full_info.last_snapshot.timestamp = int(
              mysql_utils.TimestampToRDFDatetime(last_client_ts)
          )
          c_full_info.last_snapshot.startup_info.ParseFromString(
              client_startup_obj
          )
          c_full_info.last_snapshot.startup_info.timestamp = (
              c_full_info.last_snapshot.timestamp
          )
        else:
          c_full_info.last_snapshot.client_id = db_utils.IntToClientID(cid)

        if last_startup_obj is not None:
          c_full_info.last_startup_info.ParseFromString(last_startup_obj)
          c_full_info.last_startup_info.timestamp = int(
              mysql_utils.TimestampToRDFDatetime(last_startup_ts)
          )

        if last_rrg_startup_obj is not None:
          c_full_info.last_rrg_startup.ParseFromString(last_rrg_startup_obj)

      if label_owner and label_name:
        c_full_info.labels.add(name=label_name, owner=label_owner)

      prev_cid = cid

    if c_full_info:
      yield db_utils.IntToClientID(prev_cid), c_full_info

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction(readonly=True)
  def MultiReadClientFullInfo(
      self,
      client_ids: Collection[str],
      min_last_ping: Optional[rdfvalue.RDFDatetime] = None,
      cursor: Optional[MySQLdb.cursors.Cursor] = None,
  ) -> Mapping[str, objects_pb2.ClientFullInfo]:
    """Reads full client information for a list of clients."""
    assert cursor is not None
    if not client_ids:
      return {}

    query = """
    SELECT c.client_id, c.certificate,
           UNIX_TIMESTAMP(c.last_ping),
           UNIX_TIMESTAMP(c.last_foreman),
           UNIX_TIMESTAMP(c.first_seen),
           UNIX_TIMESTAMP(c.last_snapshot_timestamp),
           UNIX_TIMESTAMP(c.last_crash_timestamp),
           UNIX_TIMESTAMP(c.last_startup_timestamp),
           h.client_snapshot,
           s.startup_info, s_last.startup_info, rrg_s_last.startup,
           l.owner_username, l.label
      FROM clients AS c FORCE INDEX (PRIMARY)
           LEFT JOIN client_snapshot_history AS h FORCE INDEX (PRIMARY)
                  ON c.client_id = h.client_id
                 AND c.last_snapshot_timestamp = h.timestamp
           LEFT JOIN client_startup_history AS s FORCE INDEX (PRIMARY)
                  ON c.client_id = s.client_id
                 AND c.last_snapshot_timestamp = s.timestamp
           LEFT JOIN client_startup_history AS s_last FORCE INDEX (PRIMARY)
                  ON c.client_id = s_last.client_id
                 AND c.last_startup_timestamp = s_last.timestamp
           LEFT JOIN client_rrg_startup_history AS rrg_s_last
                  ON rrg_s_last.id = (SELECT id
                                        FROM client_rrg_startup_history
                                       WHERE client_id = c.client_id
                                    ORDER BY timestamp DESC
                                       LIMIT 1)
           LEFT JOIN client_labels AS l FORCE INDEX (PRIMARY)
                  ON c.client_id = l.client_id
    """

    query += "WHERE c.client_id IN (%s) " % ", ".join(["%s"] * len(client_ids))

    values = [db_utils.ClientIDToInt(cid) for cid in client_ids]
    if min_last_ping is not None:
      query += "AND c.last_ping >= FROM_UNIXTIME(%s)"
      values.append(mysql_utils.RDFDatetimeToTimestamp(min_last_ping))

    cursor.execute(query, values)
    return dict(self._ResponseToClientsFullInfo(cursor.fetchall()))

  def ReadClientLastPings(
      self,
      min_last_ping: Optional[rdfvalue.RDFDatetime] = None,
      max_last_ping: Optional[rdfvalue.RDFDatetime] = None,
      batch_size: int = db.CLIENT_IDS_BATCH_SIZE,
  ) -> Iterator[Mapping[str, Optional[rdfvalue.RDFDatetime]]]:
    """Yields dicts of last-ping timestamps for clients in the DB."""
    last_client_id = db_utils.IntToClientID(0)

    while True:
      last_client_id, last_pings = self._ReadClientLastPings(
          last_client_id,
          batch_size,
          min_last_ping=min_last_ping,
          max_last_ping=max_last_ping,
      )
      if last_pings:
        yield last_pings
      if len(last_pings) < batch_size:
        break

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction(readonly=True)
  def _ReadClientLastPings(
      self,
      last_client_id: str,
      count: int,
      min_last_ping: Optional[rdfvalue.RDFDatetime] = None,
      max_last_ping: Optional[rdfvalue.RDFDatetime] = None,
      cursor: Optional[MySQLdb.cursors.Cursor] = None,
  ) -> tuple[str, Mapping[str, Optional[rdfvalue.RDFDatetime]]]:
    """Yields dicts of last-ping timestamps for clients in the DB."""
    assert cursor is not None
    where_filters = ["client_id > %s"]
    query_values = [db_utils.ClientIDToInt(last_client_id)]
    if min_last_ping is not None:
      where_filters.append("last_ping >= FROM_UNIXTIME(%s) ")
      query_values.append(mysql_utils.RDFDatetimeToTimestamp(min_last_ping))
    if max_last_ping is not None:
      where_filters.append(
          "(last_ping IS NULL OR last_ping <= FROM_UNIXTIME(%s))"
      )
      query_values.append(mysql_utils.RDFDatetimeToTimestamp(max_last_ping))

    query = """
      SELECT client_id, UNIX_TIMESTAMP(last_ping)
      FROM clients
      WHERE {}
      ORDER BY client_id
      LIMIT %s""".format(" AND ".join(where_filters))

    cursor.execute(query, query_values + [count])
    last_pings = {}
    last_client_id = None
    for int_client_id, last_ping in cursor.fetchall():
      last_client_id = db_utils.IntToClientID(int_client_id)
      last_pings[last_client_id] = mysql_utils.TimestampToRDFDatetime(last_ping)
    return last_client_id, last_pings

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction()
  def MultiAddClientKeywords(
      self,
      client_ids: Collection[str],
      keywords: Collection[str],
      cursor: Optional[MySQLdb.cursors.Cursor] = None,
  ) -> None:
    """Associates the provided keywords with the specified clients."""
    assert cursor is not None
    # Early return to avoid generating invalid SQL code.
    if not client_ids or not keywords:
      return

    args = []

    for client_id in client_ids:
      int_client_id = db_utils.ClientIDToInt(client_id)
      for keyword in keywords:
        keyword_hash = mysql_utils.Hash(keyword)
        args.append((int_client_id, keyword_hash, keyword))

    query = """
        INSERT INTO client_keywords (client_id, keyword_hash, keyword)
        VALUES {}
        ON DUPLICATE KEY UPDATE timestamp = NOW(6)
            """.format(", ".join(["(%s, %s, %s)"] * len(args)))
    try:
      cursor.execute(query, list(itertools.chain.from_iterable(args)))
    except MySQLdb.IntegrityError as error:
      raise db.AtLeastOneUnknownClientError(client_ids) from error

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction()
  def RemoveClientKeyword(
      self,
      client_id: str,
      keyword: str,
      cursor: Optional[MySQLdb.cursors.Cursor] = None,
  ) -> None:
    """Removes the association of a particular client to a keyword."""
    assert cursor is not None
    cursor.execute(
        "DELETE FROM client_keywords "
        "WHERE client_id = %s AND keyword_hash = %s",
        [db_utils.ClientIDToInt(client_id), mysql_utils.Hash(keyword)],
    )

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction(readonly=True)
  def ListClientsForKeywords(
      self,
      keywords: Collection[str],
      start_time: Optional[rdfvalue.RDFDatetime] = None,
      cursor: Optional[MySQLdb.cursors.Cursor] = None,
  ) -> Mapping[str, Collection[str]]:
    """Lists the clients associated with keywords."""
    assert cursor is not None
    keywords = set(keywords)
    hash_to_kw = {mysql_utils.Hash(kw): kw for kw in keywords}
    result = {kw: [] for kw in keywords}

    query = """
      SELECT keyword_hash, client_id
      FROM client_keywords
      FORCE INDEX (client_index_by_keyword_hash)
      WHERE keyword_hash IN ({})
    """.format(", ".join(["%s"] * len(result)))
    args = list(hash_to_kw.keys())
    if start_time:
      query += " AND timestamp >= FROM_UNIXTIME(%s)"
      args.append(mysql_utils.RDFDatetimeToTimestamp(start_time))
    cursor.execute(query, args)

    for kw_hash, cid in cursor.fetchall():
      result[hash_to_kw[kw_hash]].append(db_utils.IntToClientID(cid))
    return result

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction()
  def MultiAddClientLabels(
      self,
      client_ids: Collection[str],
      owner: str,
      labels: Collection[str],
      cursor: Optional[MySQLdb.cursors.Cursor] = None,
  ) -> None:
    """Attaches user labels to the specified clients."""
    assert cursor is not None
    # Early return to avoid generating invalid SQL code.
    if not client_ids or not labels:
      return

    args = []
    for client_id in client_ids:
      client_id_int = db_utils.ClientIDToInt(client_id)
      owner_hash = mysql_utils.Hash(owner)

      for label in labels:
        args.append((client_id_int, owner_hash, owner, label))

    query = f"""
     INSERT
     IGNORE
       INTO client_labels
            (client_id, owner_username_hash, owner_username, label)
     VALUES {", ".join(["(%s, %s, %s, %s)"] * len(args))}
    """

    args = list(itertools.chain.from_iterable(args))
    try:
      cursor.execute(query, args)
    except MySQLdb.IntegrityError as error:
      raise db.AtLeastOneUnknownClientError(client_ids) from error

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction(readonly=True)
  def MultiReadClientLabels(
      self,
      client_ids: Collection[str],
      cursor: Optional[MySQLdb.cursors.Cursor] = None,
  ) -> Mapping[str, Sequence[objects_pb2.ClientLabel]]:
    """Reads the user labels for a list of clients."""
    assert cursor is not None

    int_ids = [db_utils.ClientIDToInt(cid) for cid in client_ids]
    query = (
        "SELECT client_id, owner_username, label "
        "FROM client_labels "
        "WHERE client_id IN ({})"
    ).format(", ".join(["%s"] * len(client_ids)))

    ret = {client_id: [] for client_id in client_ids}
    cursor.execute(query, int_ids)
    for client_id, owner, label in cursor.fetchall():
      ret[db_utils.IntToClientID(client_id)].append(
          objects_pb2.ClientLabel(name=label, owner=owner)
      )

    for r in ret.values():
      r.sort(key=lambda label: (label.owner, label.name))

    return ret

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction()
  def RemoveClientLabels(
      self,
      client_id: str,
      owner: str,
      labels: Sequence[str],
      cursor: Optional[MySQLdb.cursors.Cursor] = None,
  ) -> None:
    """Removes a list of user labels from a given client."""
    assert cursor is not None

    query = (
        "DELETE FROM client_labels "
        "WHERE client_id = %s AND owner_username_hash = %s "
        "AND label IN ({})"
    ).format(", ".join(["%s"] * len(labels)))
    args = itertools.chain(
        [
            db_utils.ClientIDToInt(client_id),
            mysql_utils.Hash(owner),
        ],
        labels,
    )
    cursor.execute(query, args)

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction(readonly=True)
  def ReadAllClientLabels(self, cursor=None):
    """Reads the user labels for a list of clients."""
    assert cursor is not None

    cursor.execute("SELECT DISTINCT label FROM client_labels")

    result = []
    for (label,) in cursor.fetchall():
      result.append(label)

    return result

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction()
  def WriteClientCrashInfo(
      self,
      client_id: str,
      crash_info: jobs_pb2.ClientCrash,
      cursor: Optional[MySQLdb.cursors.Cursor] = None,
  ) -> None:
    """Writes a new client crash record."""
    assert cursor is not None
    cursor.execute("SET @now = NOW(6)")

    params = {
        "client_id": db_utils.ClientIDToInt(client_id),
        "crash_info": crash_info.SerializeToString(),
    }

    try:
      cursor.execute(
          """
      INSERT INTO client_crash_history (client_id, timestamp, crash_info)
           VALUES (%(client_id)s, @now, %(crash_info)s)
      """,
          params,
      )

      cursor.execute(
          """
      UPDATE clients
         SET last_crash_timestamp = @now
       WHERE client_id = %(client_id)s
      """,
          params,
      )

    except MySQLdb.IntegrityError as e:
      raise db.UnknownClientError(client_id, cause=e)

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction(readonly=True)
  def ReadClientCrashInfo(
      self,
      client_id: str,
      cursor: Optional[MySQLdb.cursors.Cursor] = None,
  ) -> Optional[jobs_pb2.ClientCrash]:
    """Reads the latest client crash record for a single client."""
    assert cursor is not None
    cursor.execute(
        "SELECT UNIX_TIMESTAMP(timestamp), crash_info "
        "FROM clients, client_crash_history WHERE "
        "clients.client_id = client_crash_history.client_id AND "
        "clients.last_crash_timestamp = client_crash_history.timestamp AND "
        "clients.client_id = %s",
        [db_utils.ClientIDToInt(client_id)],
    )
    row = cursor.fetchone()
    if not row:
      return None

    timestamp, crash_info = row
    res = jobs_pb2.ClientCrash()
    res.ParseFromString(crash_info)
    res.timestamp = int(mysql_utils.TimestampToRDFDatetime(timestamp))
    return res

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction(readonly=True)
  def ReadClientCrashInfoHistory(
      self,
      client_id: str,
      cursor: Optional[MySQLdb.cursors.Cursor] = None,
  ) -> Sequence[jobs_pb2.ClientCrash]:
    """Reads the full crash history for a particular client."""
    assert cursor is not None
    cursor.execute(
        "SELECT UNIX_TIMESTAMP(timestamp), crash_info "
        "FROM client_crash_history WHERE "
        "client_crash_history.client_id = %s "
        "ORDER BY timestamp DESC",
        [db_utils.ClientIDToInt(client_id)],
    )
    ret = []
    for timestamp, crash_info in cursor.fetchall():
      ci = jobs_pb2.ClientCrash()
      ci.ParseFromString(crash_info)
      ci.timestamp = int(mysql_utils.TimestampToRDFDatetime(timestamp))
      ret.append(ci)
    return ret

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction()
  def DeleteClient(
      self,
      client_id: str,
      cursor: Optional[MySQLdb.cursors.Cursor] = None,
  ) -> None:
    """Deletes a client with all associated metadata."""
    assert cursor is not None
    cursor.execute(
        "SELECT COUNT(*) FROM clients WHERE client_id = %s",
        [db_utils.ClientIDToInt(client_id)],
    )

    if cursor.fetchone()[0] == 0:
      raise db.UnknownClientError(client_id)

    # Clean out foreign keys first.
    cursor.execute(
        """
    UPDATE clients SET
      last_crash_timestamp = NULL,
      last_snapshot_timestamp = NULL,
      last_startup_timestamp = NULL
    WHERE client_id = %s""",
        [db_utils.ClientIDToInt(client_id)],
    )

    cursor.execute(
        "DELETE FROM clients WHERE client_id = %s",
        [db_utils.ClientIDToInt(client_id)],
    )


# We use the same value as other database implementations that we have some
# measures for. However, MySQL has different performance characteristics and it
# could be fine-tuned if possible.
_DEFAULT_CLIENT_STATS_BATCH_SIZE = 10_000
