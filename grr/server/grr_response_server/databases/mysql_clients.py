#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""The MySQL database methods for client handling."""
from __future__ import absolute_import
from __future__ import division

from __future__ import unicode_literals

import collections


from future.utils import iterkeys
from future.utils import itervalues

import MySQLdb
from MySQLdb.constants import ER as mysql_error_constants

from typing import Generator, List, Text

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_network as rdf_client_network
from grr_response_core.lib.rdfvalues import client_stats as rdf_client_stats
from grr_response_core.lib.util import collection
from grr_response_server.databases import db
from grr_response_server.databases import db_utils
from grr_response_server.databases import mysql_utils
from grr_response_server.rdfvalues import objects as rdf_objects


class MySQLDBClientMixin(object):
  """MySQLDataStore mixin for client related functions."""

  @mysql_utils.WithTransaction()
  def WriteClientMetadata(self,
                          client_id,
                          certificate=None,
                          fleetspeak_enabled=None,
                          first_seen=None,
                          last_ping=None,
                          last_clock=None,
                          last_ip=None,
                          last_foreman=None,
                          cursor=None):
    """Write metadata about the client."""
    placeholders = []
    values = collections.OrderedDict()

    placeholders.append("%(client_id)s")
    values["client_id"] = db_utils.ClientIDToInt(client_id)

    if certificate:
      placeholders.append("%(certificate)s")
      values["certificate"] = certificate.SerializeToString()
    if fleetspeak_enabled is not None:
      placeholders.append("%(fleetspeak_enabled)s")
      values["fleetspeak_enabled"] = fleetspeak_enabled
    if first_seen is not None:
      placeholders.append("FROM_UNIXTIME(%(first_seen)s)")
      values["first_seen"] = mysql_utils.RDFDatetimeToTimestamp(first_seen)
    if last_ping is not None:
      placeholders.append("FROM_UNIXTIME(%(last_ping)s)")
      values["last_ping"] = mysql_utils.RDFDatetimeToTimestamp(last_ping)
    if last_clock:
      placeholders.append("FROM_UNIXTIME(%(last_clock)s)")
      values["last_clock"] = mysql_utils.RDFDatetimeToTimestamp(last_clock)
    if last_ip:
      placeholders.append("%(last_ip)s")
      values["last_ip"] = last_ip.SerializeToString()
    if last_foreman:
      placeholders.append("FROM_UNIXTIME(%(last_foreman)s)")
      values["last_foreman"] = mysql_utils.RDFDatetimeToTimestamp(last_foreman)

    updates = []
    for column in iterkeys(values):
      updates.append("{column} = VALUES({column})".format(column=column))

    query = """
    INSERT INTO clients ({columns})
    VALUES ({placeholders})
    ON DUPLICATE KEY UPDATE {updates}
    """.format(
        columns=", ".join(iterkeys(values)),
        placeholders=", ".join(placeholders),
        updates=", ".join(updates))

    cursor.execute(query, values)

  @mysql_utils.WithTransaction(readonly=True)
  def MultiReadClientMetadata(self, client_ids, cursor=None):
    """Reads ClientMetadata records for a list of clients."""
    ids = [db_utils.ClientIDToInt(client_id) for client_id in client_ids]
    query = ("SELECT client_id, fleetspeak_enabled, certificate, "
             "UNIX_TIMESTAMP(last_ping), "
             "UNIX_TIMESTAMP(last_clock), last_ip, "
             "UNIX_TIMESTAMP(last_foreman), UNIX_TIMESTAMP(first_seen), "
             "UNIX_TIMESTAMP(last_crash_timestamp), "
             "UNIX_TIMESTAMP(last_startup_timestamp) FROM "
             "clients WHERE client_id IN ({})").format(", ".join(["%s"] *
                                                                 len(ids)))
    ret = {}
    cursor.execute(query, ids)
    while True:
      row = cursor.fetchone()
      if not row:
        break
      cid, fs, crt, ping, clk, ip, foreman, first, lct, lst = row
      ret[db_utils.IntToClientID(cid)] = rdf_objects.ClientMetadata(
          certificate=crt,
          fleetspeak_enabled=fs,
          first_seen=mysql_utils.TimestampToRDFDatetime(first),
          ping=mysql_utils.TimestampToRDFDatetime(ping),
          clock=mysql_utils.TimestampToRDFDatetime(clk),
          ip=mysql_utils.StringToRDFProto(rdf_client_network.NetworkAddress,
                                          ip),
          last_foreman_time=mysql_utils.TimestampToRDFDatetime(foreman),
          startup_info_timestamp=mysql_utils.TimestampToRDFDatetime(lst),
          last_crash_timestamp=mysql_utils.TimestampToRDFDatetime(lct))
    return ret

  @mysql_utils.WithTransaction()
  def WriteClientSnapshot(self, snapshot, cursor=None):
    """Write new client snapshot."""
    insert_history_query = (
        "INSERT INTO client_snapshot_history(client_id, timestamp, "
        "client_snapshot) VALUES (%s, FROM_UNIXTIME(%s), %s)")
    insert_startup_query = (
        "INSERT INTO client_startup_history(client_id, timestamp, "
        "startup_info) VALUES(%s, FROM_UNIXTIME(%s), %s)")

    now = rdfvalue.RDFDatetime.Now()

    client_platform = snapshot.knowledge_base.os
    current_timestamp = mysql_utils.RDFDatetimeToTimestamp(now)
    client_info = {
        "last_snapshot_timestamp": current_timestamp,
        "last_startup_timestamp": current_timestamp,
        "last_version_string": snapshot.GetGRRVersionString(),
        "last_platform_release": snapshot.Uname(),
    }
    update_clauses = [
        "last_snapshot_timestamp = FROM_UNIXTIME(%(last_snapshot_timestamp)s)",
        "last_startup_timestamp = FROM_UNIXTIME(%(last_startup_timestamp)s)",
        "last_version_string = %(last_version_string)s",
        "last_platform_release = %(last_platform_release)s",
    ]
    if client_platform:
      client_info["last_platform"] = client_platform
      update_clauses.append("last_platform = %(last_platform)s")

    update_query = (
        "UPDATE clients SET {} WHERE client_id = %(client_id)s".format(
            ", ".join(update_clauses)))

    int_client_id = db_utils.ClientIDToInt(snapshot.client_id)
    client_info["client_id"] = int_client_id

    startup_info = snapshot.startup_info
    snapshot.startup_info = None
    try:
      cursor.execute(
          insert_history_query,
          (int_client_id, current_timestamp, snapshot.SerializeToString()))
      cursor.execute(
          insert_startup_query,
          (int_client_id, current_timestamp, startup_info.SerializeToString()))
      cursor.execute(update_query, client_info)
    except MySQLdb.IntegrityError as e:
      raise db.UnknownClientError(snapshot.client_id, cause=e)
    finally:
      snapshot.startup_info = startup_info

  @mysql_utils.WithTransaction(readonly=True)
  def MultiReadClientSnapshot(self, client_ids, cursor=None):
    """Reads the latest client snapshots for a list of clients."""
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
        "AND c.client_id IN ({})").format(", ".join(["%s"] * len(client_ids)))
    ret = {cid: None for cid in client_ids}
    cursor.execute(query, int_ids)

    while True:
      row = cursor.fetchone()
      if not row:
        break
      cid, snapshot, timestamp, startup_info = row
      client_obj = mysql_utils.StringToRDFProto(rdf_objects.ClientSnapshot,
                                                snapshot)
      client_obj.startup_info = mysql_utils.StringToRDFProto(
          rdf_client.StartupInfo, startup_info)
      client_obj.timestamp = mysql_utils.TimestampToRDFDatetime(timestamp)
      ret[db_utils.IntToClientID(cid)] = client_obj
    return ret

  @mysql_utils.WithTransaction(readonly=True)
  def ReadClientSnapshotHistory(self, client_id, timerange=None, cursor=None):
    """Reads the full history for a particular client."""

    client_id_int = db_utils.ClientIDToInt(client_id)

    query = ("SELECT sn.client_snapshot, st.startup_info, "
             "       UNIX_TIMESTAMP(sn.timestamp) FROM "
             "client_snapshot_history AS sn, "
             "client_startup_history AS st WHERE "
             "sn.client_id = st.client_id AND "
             "sn.timestamp = st.timestamp AND "
             "sn.client_id=%s ")

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
    for snapshot, startup_info, timestamp in cursor.fetchall():
      client = rdf_objects.ClientSnapshot.FromSerializedString(snapshot)
      client.startup_info = rdf_client.StartupInfo.FromSerializedString(
          startup_info)
      client.timestamp = mysql_utils.TimestampToRDFDatetime(timestamp)

      ret.append(client)
    return ret

  @mysql_utils.WithTransaction()
  def WriteClientSnapshotHistory(self, clients, cursor=None):
    """Writes the full history for a particular client."""
    client_id = clients[0].client_id
    latest_timestamp = max(client.timestamp for client in clients)

    base_params = {
        "client_id": db_utils.ClientIDToInt(client_id),
        "latest_timestamp": mysql_utils.RDFDatetimeToTimestamp(latest_timestamp)
    }

    try:
      for client in clients:
        startup_info = client.startup_info
        client.startup_info = None

        params = base_params.copy()
        params.update({
            "timestamp": mysql_utils.RDFDatetimeToTimestamp(client.timestamp),
            "client_snapshot": client.SerializeToString(),
            "startup_info": startup_info.SerializeToString(),
        })

        cursor.execute(
            """
        INSERT INTO client_snapshot_history (client_id, timestamp,
                                             client_snapshot)
        VALUES (%(client_id)s, FROM_UNIXTIME(%(timestamp)s),
                %(client_snapshot)s)
        """, params)

        cursor.execute(
            """
        INSERT INTO client_startup_history (client_id, timestamp,
                                            startup_info)
        VALUES (%(client_id)s, FROM_UNIXTIME(%(timestamp)s),
                %(startup_info)s)
        """, params)

        client.startup_info = startup_info

      cursor.execute(
          """
      UPDATE clients
         SET last_snapshot_timestamp = FROM_UNIXTIME(%(latest_timestamp)s)
       WHERE client_id = %(client_id)s
         AND (last_snapshot_timestamp IS NULL OR
              last_snapshot_timestamp < FROM_UNIXTIME(%(latest_timestamp)s))
      """, base_params)

      cursor.execute(
          """
      UPDATE clients
         SET last_startup_timestamp = FROM_UNIXTIME(%(latest_timestamp)s)
       WHERE client_id = %(client_id)s
         AND (last_startup_timestamp IS NULL OR
              last_startup_timestamp < FROM_UNIXTIME(%(latest_timestamp)s))
      """, base_params)
    except MySQLdb.IntegrityError as error:
      raise db.UnknownClientError(client_id, cause=error)

  @mysql_utils.WithTransaction()
  def WriteClientStartupInfo(self, client_id, startup_info, cursor=None):
    """Writes a new client startup record."""
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
          """, params)

      cursor.execute(
          """
      UPDATE clients
         SET last_startup_timestamp = @now
       WHERE client_id = %(client_id)s
      """, params)
    except MySQLdb.IntegrityError as e:
      raise db.UnknownClientError(client_id, cause=e)

  @mysql_utils.WithTransaction(readonly=True)
  def ReadClientStartupInfo(self, client_id, cursor=None):
    """Reads the latest client startup record for a single client."""
    query = (
        "SELECT startup_info, UNIX_TIMESTAMP(timestamp) "
        "FROM clients, client_startup_history "
        "WHERE clients.last_startup_timestamp=client_startup_history.timestamp "
        "AND clients.client_id=client_startup_history.client_id "
        "AND clients.client_id=%s")
    cursor.execute(query, [db_utils.ClientIDToInt(client_id)])
    row = cursor.fetchone()
    if row is None:
      return None

    startup_info, timestamp = row
    res = rdf_client.StartupInfo.FromSerializedString(startup_info)
    res.timestamp = mysql_utils.TimestampToRDFDatetime(timestamp)
    return res

  @mysql_utils.WithTransaction(readonly=True)
  def ReadClientStartupInfoHistory(self, client_id, timerange=None,
                                   cursor=None):
    """Reads the full startup history for a particular client."""

    client_id_int = db_utils.ClientIDToInt(client_id)

    query = ("SELECT startup_info, UNIX_TIMESTAMP(timestamp) "
             "FROM client_startup_history "
             "WHERE client_id=%s ")
    args = [client_id_int]

    if timerange:
      time_from, time_to = timerange  # pylint: disable=unpacking-non-sequence

      if time_from is not None:
        query += "AND timestamp >= FROM_UNIXTIME(%s) "
        args.append(mysql_utils.RDFDatetimeToTimestamp(time_from))

      if time_to is not None:
        query += "AND timestamp <= FROM_UNIXTIME(%s) "
        args.append(mysql_utils.RDFDatetimeToTimestamp(time_to))

    query += "ORDER BY timestamp DESC "

    ret = []
    cursor.execute(query, args)

    for startup_info, timestamp in cursor.fetchall():
      si = rdf_client.StartupInfo.FromSerializedString(startup_info)
      si.timestamp = mysql_utils.TimestampToRDFDatetime(timestamp)
      ret.append(si)
    return ret

  def _ResponseToClientsFullInfo(self, response):
    """Creates a ClientFullInfo object from a database response."""
    c_full_info = None
    prev_cid = None
    for row in response:
      (cid, fs, crt, ping, clk, ip, foreman, first, last_client_ts,
       last_crash_ts, last_startup_ts, client_obj, client_startup_obj,
       last_startup_obj, label_owner, label_name) = row

      if cid != prev_cid:
        if c_full_info:
          yield db_utils.IntToClientID(prev_cid), c_full_info

        metadata = rdf_objects.ClientMetadata(
            certificate=crt,
            fleetspeak_enabled=fs,
            first_seen=mysql_utils.TimestampToRDFDatetime(first),
            ping=mysql_utils.TimestampToRDFDatetime(ping),
            clock=mysql_utils.TimestampToRDFDatetime(clk),
            ip=mysql_utils.StringToRDFProto(rdf_client_network.NetworkAddress,
                                            ip),
            last_foreman_time=mysql_utils.TimestampToRDFDatetime(foreman),
            startup_info_timestamp=mysql_utils.TimestampToRDFDatetime(
                last_startup_ts),
            last_crash_timestamp=mysql_utils.TimestampToRDFDatetime(
                last_crash_ts))

        if client_obj is not None:
          l_snapshot = rdf_objects.ClientSnapshot.FromSerializedString(
              client_obj)
          l_snapshot.timestamp = mysql_utils.TimestampToRDFDatetime(
              last_client_ts)
          l_snapshot.startup_info = rdf_client.StartupInfo.FromSerializedString(
              client_startup_obj)
          l_snapshot.startup_info.timestamp = l_snapshot.timestamp
        else:
          l_snapshot = rdf_objects.ClientSnapshot(
              client_id=db_utils.IntToClientID(cid))

        if last_startup_obj is not None:
          startup_info = rdf_client.StartupInfo.FromSerializedString(
              last_startup_obj)
          startup_info.timestamp = mysql_utils.TimestampToRDFDatetime(
              last_startup_ts)
        else:
          startup_info = None

        prev_cid = cid
        c_full_info = rdf_objects.ClientFullInfo(
            metadata=metadata,
            labels=[],
            last_snapshot=l_snapshot,
            last_startup_info=startup_info)

      if label_owner and label_name:
        c_full_info.labels.append(
            rdf_objects.ClientLabel(name=label_name, owner=label_owner))

    if c_full_info:
      yield db_utils.IntToClientID(prev_cid), c_full_info

  @mysql_utils.WithTransaction(readonly=True)
  def MultiReadClientFullInfo(self, client_ids, min_last_ping=None,
                              cursor=None):
    """Reads full client information for a list of clients."""
    if not client_ids:
      return {}

    query = (
        "SELECT "
        "c.client_id, c.fleetspeak_enabled, c.certificate, "
        "UNIX_TIMESTAMP(c.last_ping), UNIX_TIMESTAMP(c.last_clock), "
        "c.last_ip, UNIX_TIMESTAMP(c.last_foreman), "
        "UNIX_TIMESTAMP(c.first_seen), "
        "UNIX_TIMESTAMP(c.last_snapshot_timestamp), "
        "UNIX_TIMESTAMP(c.last_crash_timestamp), "
        "UNIX_TIMESTAMP(c.last_startup_timestamp), "
        "h.client_snapshot, s.startup_info, s_last.startup_info, "
        "l.owner_username, l.label "
        "FROM clients as c "
        "FORCE INDEX (PRIMARY) "
        "LEFT JOIN client_snapshot_history as h FORCE INDEX (PRIMARY) ON ( "
        "c.client_id = h.client_id AND "
        "h.timestamp = c.last_snapshot_timestamp) "
        "LEFT JOIN client_startup_history as s FORCE INDEX (PRIMARY) ON ( "
        "c.client_id = s.client_id AND "
        "s.timestamp = c.last_snapshot_timestamp) "
        "LEFT JOIN client_startup_history as s_last FORCE INDEX (PRIMARY) ON ( "
        "c.client_id = s_last.client_id "
        "AND s_last.timestamp = c.last_startup_timestamp) "
        "LEFT JOIN client_labels AS l FORCE INDEX (PRIMARY) "
        "ON (c.client_id = l.client_id) ")

    query += "WHERE c.client_id IN (%s) " % ", ".join(["%s"] * len(client_ids))

    values = [db_utils.ClientIDToInt(cid) for cid in client_ids]
    if min_last_ping is not None:
      query += "AND c.last_ping >= FROM_UNIXTIME(%s)"
      values.append(mysql_utils.RDFDatetimeToTimestamp(min_last_ping))

    cursor.execute(query, values)
    return dict(self._ResponseToClientsFullInfo(cursor.fetchall()))

  def ReadClientLastPings(self,
                          min_last_ping=None,
                          max_last_ping=None,
                          fleetspeak_enabled=None,
                          batch_size=db.CLIENT_IDS_BATCH_SIZE):
    """Yields dicts of last-ping timestamps for clients in the DB."""
    last_client_id = db_utils.IntToClientID(0)

    while True:
      last_client_id, last_pings = self._ReadClientLastPings(
          last_client_id,
          batch_size,
          min_last_ping=min_last_ping,
          max_last_ping=max_last_ping,
          fleetspeak_enabled=fleetspeak_enabled)
      if last_pings:
        yield last_pings
      if len(last_pings) < batch_size:
        break

  @mysql_utils.WithTransaction(readonly=True)
  def _ReadClientLastPings(self,
                           last_client_id,
                           count,
                           min_last_ping=None,
                           max_last_ping=None,
                           fleetspeak_enabled=None,
                           cursor=None):
    """Yields dicts of last-ping timestamps for clients in the DB."""
    where_filters = ["client_id > %s"]
    query_values = [db_utils.ClientIDToInt(last_client_id)]
    if min_last_ping is not None:
      where_filters.append("last_ping >= FROM_UNIXTIME(%s) ")
      query_values.append(mysql_utils.RDFDatetimeToTimestamp(min_last_ping))
    if max_last_ping is not None:
      where_filters.append(
          "(last_ping IS NULL OR last_ping <= FROM_UNIXTIME(%s))")
      query_values.append(mysql_utils.RDFDatetimeToTimestamp(max_last_ping))
    if fleetspeak_enabled is not None:
      if fleetspeak_enabled:
        where_filters.append("fleetspeak_enabled IS TRUE")
      else:
        where_filters.append(
            "(fleetspeak_enabled IS NULL OR fleetspeak_enabled IS FALSE)")

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

  @mysql_utils.WithTransaction()
  def AddClientKeywords(self, client_id, keywords, cursor=None):
    """Associates the provided keywords with the client."""
    cid = db_utils.ClientIDToInt(client_id)
    keywords = set(keywords)
    args = [(cid, mysql_utils.Hash(kw), kw) for kw in keywords]
    args = list(collection.Flatten(args))

    query = """
        INSERT INTO client_keywords (client_id, keyword_hash, keyword)
        VALUES {}
        ON DUPLICATE KEY UPDATE timestamp = NOW(6)
            """.format(", ".join(["(%s, %s, %s)"] * len(keywords)))
    try:
      cursor.execute(query, args)
    except MySQLdb.IntegrityError as e:
      raise db.UnknownClientError(client_id, cause=e)

  @mysql_utils.WithTransaction()
  def RemoveClientKeyword(self, client_id, keyword, cursor=None):
    """Removes the association of a particular client to a keyword."""
    cursor.execute(
        "DELETE FROM client_keywords "
        "WHERE client_id = %s AND keyword_hash = %s",
        [db_utils.ClientIDToInt(client_id),
         mysql_utils.Hash(keyword)])

  @mysql_utils.WithTransaction(readonly=True)
  def ListClientsForKeywords(self, keywords, start_time=None, cursor=None):
    """Lists the clients associated with keywords."""
    keywords = set(keywords)
    hash_to_kw = {mysql_utils.Hash(kw): kw for kw in keywords}
    result = {kw: [] for kw in keywords}

    query = """
      SELECT keyword_hash, client_id
      FROM client_keywords
      FORCE INDEX (client_index_by_keyword_hash)
      WHERE keyword_hash IN ({})
    """.format(", ".join(["%s"] * len(result)))
    args = list(iterkeys(hash_to_kw))
    if start_time:
      query += " AND timestamp >= FROM_UNIXTIME(%s)"
      args.append(mysql_utils.RDFDatetimeToTimestamp(start_time))
    cursor.execute(query, args)

    for kw_hash, cid in cursor.fetchall():
      result[hash_to_kw[kw_hash]].append(db_utils.IntToClientID(cid))
    return result

  @mysql_utils.WithTransaction()
  def AddClientLabels(self, client_id, owner, labels, cursor=None):
    """Attaches a list of user labels to a client."""
    cid = db_utils.ClientIDToInt(client_id)
    labels = set(labels)
    args = [(cid, mysql_utils.Hash(owner), owner, label) for label in labels]
    args = list(collection.Flatten(args))

    query = """
          INSERT IGNORE INTO client_labels
              (client_id, owner_username_hash, owner_username, label)
          VALUES {}
          """.format(", ".join(["(%s, %s, %s, %s)"] * len(labels)))
    try:
      cursor.execute(query, args)
    except MySQLdb.IntegrityError as e:
      raise db.UnknownClientError(client_id, cause=e)

  @mysql_utils.WithTransaction(readonly=True)
  def MultiReadClientLabels(self, client_ids, cursor=None):
    """Reads the user labels for a list of clients."""

    int_ids = [db_utils.ClientIDToInt(cid) for cid in client_ids]
    query = ("SELECT client_id, owner_username, label "
             "FROM client_labels "
             "WHERE client_id IN ({})").format(", ".join(["%s"] *
                                                         len(client_ids)))

    ret = {client_id: [] for client_id in client_ids}
    cursor.execute(query, int_ids)
    for client_id, owner, label in cursor.fetchall():
      ret[db_utils.IntToClientID(client_id)].append(
          rdf_objects.ClientLabel(name=label, owner=owner))

    for r in itervalues(ret):
      r.sort(key=lambda label: (label.owner, label.name))
    return ret

  @mysql_utils.WithTransaction()
  def RemoveClientLabels(self, client_id, owner, labels, cursor=None):
    """Removes a list of user labels from a given client."""

    query = ("DELETE FROM client_labels "
             "WHERE client_id = %s AND owner_username_hash = %s "
             "AND label IN ({})").format(", ".join(["%s"] * len(labels)))
    args = [db_utils.ClientIDToInt(client_id), mysql_utils.Hash(owner)] + labels
    cursor.execute(query, args)

  @mysql_utils.WithTransaction(readonly=True)
  def ReadAllClientLabels(self, cursor=None):
    """Reads the user labels for a list of clients."""

    cursor.execute("SELECT DISTINCT owner_username, label FROM client_labels")

    result = []
    for owner, label in cursor.fetchall():
      result.append(rdf_objects.ClientLabel(name=label, owner=owner))

    result.sort(key=lambda label: (label.owner, label.name))
    return result

  @mysql_utils.WithTransaction()
  def WriteClientCrashInfo(self, client_id, crash_info, cursor=None):
    """Writes a new client crash record."""
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
      """, params)

      cursor.execute(
          """
      UPDATE clients
         SET last_crash_timestamp = @now
       WHERE client_id = %(client_id)s
      """, params)

    except MySQLdb.IntegrityError as e:
      raise db.UnknownClientError(client_id, cause=e)

  @mysql_utils.WithTransaction(readonly=True)
  def ReadClientCrashInfo(self, client_id, cursor=None):
    """Reads the latest client crash record for a single client."""
    cursor.execute(
        "SELECT UNIX_TIMESTAMP(timestamp), crash_info "
        "FROM clients, client_crash_history WHERE "
        "clients.client_id = client_crash_history.client_id AND "
        "clients.last_crash_timestamp = client_crash_history.timestamp AND "
        "clients.client_id = %s", [db_utils.ClientIDToInt(client_id)])
    row = cursor.fetchone()
    if not row:
      return None

    timestamp, crash_info = row
    res = rdf_client.ClientCrash.FromSerializedString(crash_info)
    res.timestamp = mysql_utils.TimestampToRDFDatetime(timestamp)
    return res

  @mysql_utils.WithTransaction(readonly=True)
  def ReadClientCrashInfoHistory(self, client_id, cursor=None):
    """Reads the full crash history for a particular client."""
    cursor.execute(
        "SELECT UNIX_TIMESTAMP(timestamp), crash_info "
        "FROM client_crash_history WHERE "
        "client_crash_history.client_id = %s "
        "ORDER BY timestamp DESC", [db_utils.ClientIDToInt(client_id)])
    ret = []
    for timestamp, crash_info in cursor.fetchall():
      ci = rdf_client.ClientCrash.FromSerializedString(crash_info)
      ci.timestamp = mysql_utils.TimestampToRDFDatetime(timestamp)
      ret.append(ci)
    return ret

  @mysql_utils.WithTransaction()
  def WriteClientStats(self,
                       client_id,
                       stats,
                       cursor=None):
    """Stores a ClientStats instance."""

    try:
      cursor.execute(
          """
          INSERT INTO client_stats (client_id, payload, timestamp)
          VALUES (%s, %s, FROM_UNIXTIME(%s))
          ON DUPLICATE KEY UPDATE payload=VALUES(payload)
          """, [
              db_utils.ClientIDToInt(client_id),
              stats.SerializeToString(),
              mysql_utils.RDFDatetimeToTimestamp(rdfvalue.RDFDatetime.Now())
          ])
    except MySQLdb.IntegrityError as e:
      if e.args[0] == mysql_error_constants.NO_REFERENCED_ROW_2:
        raise db.UnknownClientError(client_id, cause=e)
      else:
        raise

  @mysql_utils.WithTransaction(readonly=True)
  def ReadClientStats(self,
                      client_id,
                      min_timestamp,
                      max_timestamp,
                      cursor=None):
    """Reads ClientStats for a given client and time range."""

    cursor.execute(
        """
        SELECT payload FROM client_stats
        WHERE client_id = %s
          AND timestamp BETWEEN FROM_UNIXTIME(%s) AND FROM_UNIXTIME(%s)
        ORDER BY timestamp ASC
        """, [
            db_utils.ClientIDToInt(client_id),
            mysql_utils.RDFDatetimeToTimestamp(min_timestamp),
            mysql_utils.RDFDatetimeToTimestamp(max_timestamp)
        ])
    return [
        rdf_client_stats.ClientStats.FromSerializedString(stats_bytes)
        for stats_bytes, in cursor.fetchall()
    ]

  # DeleteOldClientStats does not use a single transaction, since it runs for
  # a long time. Instead, it uses multiple transactions internally.
  def DeleteOldClientStats(self, yield_after_count,
                           retention_time
                          ):
    """Deletes ClientStats older than a given timestamp."""

    while True:
      deleted_count = self._DeleteClientStats(
          limit=yield_after_count, retention_time=retention_time)

      # Do not yield a trailing 0 which occurs when an exact multiple of
      # `yield_after_count` rows were in the table.
      if deleted_count > 0:
        yield deleted_count

      # Return, when no more rows can be deleted, indicated by a transaction
      # that does not reach the deletion limit.
      if deleted_count < yield_after_count:
        return

  @mysql_utils.WithTransaction()
  def _DeleteClientStats(self,
                         limit,
                         retention_time,
                         cursor=None):
    """Deletes up to `limit` ClientStats older than `retention_time`."""
    cursor.execute(
        "DELETE FROM client_stats WHERE timestamp < FROM_UNIXTIME(%s) LIMIT %s",
        [mysql_utils.RDFDatetimeToTimestamp(retention_time), limit])
    return cursor.rowcount

  @mysql_utils.WithTransaction(readonly=True)
  def CountClientVersionStringsByLabel(self, day_buckets, cursor):
    """Computes client-activity stats for all GRR versions in the DB."""
    return self._CountClientStatisticByLabel("last_version_string", day_buckets,
                                             cursor)

  @mysql_utils.WithTransaction(readonly=True)
  def CountClientPlatformsByLabel(self, day_buckets, cursor):
    """Computes client-activity stats for all client platforms in the DB."""
    return self._CountClientStatisticByLabel("last_platform", day_buckets,
                                             cursor)

  @mysql_utils.WithTransaction(readonly=True)
  def CountClientPlatformReleasesByLabel(self, day_buckets, cursor):
    """Computes client-activity stats for OS-release strings in the DB."""
    return self._CountClientStatisticByLabel("last_platform_release",
                                             day_buckets, cursor)

  def _CountClientStatisticByLabel(self, statistic, day_buckets, cursor):
    """Returns client-activity metrics for a given statistic.

    Args:
      statistic: The name of the statistic, which should also be a column in the
        'clients' table.
      day_buckets: A set of n-day-active buckets.
      cursor: MySQL cursor for executing queries.
    """
    day_buckets = sorted(day_buckets)
    sum_clauses = []
    ping_cast_clauses = []
    timestamp_buckets = []
    now = rdfvalue.RDFDatetime.Now()

    for day_bucket in day_buckets:
      column_name = "days_active_{}".format(day_bucket)
      sum_clauses.append(
          "CAST(SUM({0}) AS UNSIGNED) AS {0}".format(column_name))
      ping_cast_clauses.append(
          "CAST(c.last_ping > FROM_UNIXTIME(%s) AS UNSIGNED) AS {}".format(
              column_name))
      timestamp_bucket = now - rdfvalue.Duration.FromDays(day_bucket)
      timestamp_buckets.append(
          mysql_utils.RDFDatetimeToTimestamp(timestamp_bucket))

    query = """
    SELECT j.{statistic}, j.label, {sum_clauses}
    FROM (
      SELECT c.{statistic} AS {statistic}, l.label AS label, {ping_cast_clauses}
      FROM clients c
      LEFT JOIN client_labels l USING(client_id)
      WHERE c.last_ping IS NOT NULL AND l.owner_username = 'GRR'
    ) AS j
    GROUP BY j.{statistic}, j.label
    """.format(
        statistic=statistic,
        sum_clauses=", ".join(sum_clauses),
        ping_cast_clauses=", ".join(ping_cast_clauses))

    cursor.execute(query, timestamp_buckets)

    counts = {}
    for response_row in cursor.fetchall():
      statistic_value, client_label = response_row[:2]
      for i, num_actives in enumerate(response_row[2:]):
        if num_actives <= 0:
          continue
        stats_key = (statistic_value, client_label, day_buckets[i])
        counts[stats_key] = num_actives
    return counts
