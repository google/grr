#!/usr/bin/env python
"""The MySQL database methods for client handling."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import datetime


from future.utils import iterkeys
from future.utils import itervalues
import MySQLdb

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_network as rdf_client_network
from grr_response_server import db
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

    columns = ["client_id"]
    values = [mysql_utils.ClientIDToInt(client_id)]
    if certificate:
      columns.append("certificate")
      values.append(certificate.SerializeToString())
    if fleetspeak_enabled is not None:
      columns.append("fleetspeak_enabled")
      values.append(int(fleetspeak_enabled))
    if first_seen:
      columns.append("first_seen")
      values.append(mysql_utils.RDFDatetimeToMysqlString(first_seen))
    if last_ping:
      columns.append("last_ping")
      values.append(mysql_utils.RDFDatetimeToMysqlString(last_ping))
    if last_clock:
      columns.append("last_clock")
      values.append(mysql_utils.RDFDatetimeToMysqlString(last_clock))
    if last_ip:
      columns.append("last_ip")
      values.append(last_ip.SerializeToString())
    if last_foreman:
      columns.append("last_foreman")
      values.append(mysql_utils.RDFDatetimeToMysqlString(last_foreman))

    query = ("INSERT INTO clients ({cols}) VALUES ({vals}) "
             "ON DUPLICATE KEY UPDATE {updates}").format(
                 cols=", ".join(columns),
                 vals=", ".join(["%s"] * len(columns)),
                 updates=", ".join([
                     "{c} = VALUES ({c})".format(c=col) for col in columns[1:]
                 ]))
    cursor.execute(query, values)

  @mysql_utils.WithTransaction(readonly=True)
  def MultiReadClientMetadata(self, client_ids, cursor=None):
    """Reads ClientMetadata records for a list of clients."""
    ids = [mysql_utils.ClientIDToInt(client_id) for client_id in client_ids]
    query = ("SELECT client_id, fleetspeak_enabled, certificate, last_ping, "
             "last_clock, last_ip, last_foreman, first_seen, "
             "last_crash_timestamp, last_startup_timestamp FROM "
             "clients WHERE client_id IN ({})").format(", ".join(
                 ["%s"] * len(ids)))
    ret = {}
    cursor.execute(query, ids)
    while True:
      row = cursor.fetchone()
      if not row:
        break
      cid, fs, crt, ping, clk, ip, foreman, first, lct, lst = row
      ret[mysql_utils.IntToClientID(cid)] = rdf_objects.ClientMetadata(
          certificate=crt,
          fleetspeak_enabled=fs,
          first_seen=mysql_utils.MysqlToRDFDatetime(first),
          ping=mysql_utils.MysqlToRDFDatetime(ping),
          clock=mysql_utils.MysqlToRDFDatetime(clk),
          ip=mysql_utils.StringToRDFProto(rdf_client_network.NetworkAddress,
                                          ip),
          last_foreman_time=mysql_utils.MysqlToRDFDatetime(foreman),
          startup_info_timestamp=mysql_utils.MysqlToRDFDatetime(lst),
          last_crash_timestamp=mysql_utils.MysqlToRDFDatetime(lct))
    return ret

  @mysql_utils.WithTransaction()
  def WriteClientSnapshot(self, client, cursor=None):
    """Write new client snapshot."""
    startup_info = client.startup_info
    client.startup_info = None

    insert_history_query = (
        "INSERT INTO client_snapshot_history(client_id, timestamp, "
        "client_snapshot) VALUES (%s, %s, %s)")
    insert_startup_query = (
        "INSERT INTO client_startup_history(client_id, timestamp, "
        "startup_info) VALUES(%s, %s, %s)")
    update_query = ("UPDATE clients SET last_client_timestamp=%s, "
                    "last_startup_timestamp=%s "
                    "WHERE client_id = %s")

    int_id = mysql_utils.ClientIDToInt(client.client_id)
    timestamp = datetime.datetime.utcnow()

    try:
      cursor.execute(insert_history_query,
                     (int_id, timestamp, client.SerializeToString()))
      cursor.execute(insert_startup_query,
                     (int_id, timestamp, startup_info.SerializeToString()))
      cursor.execute(update_query, (timestamp, timestamp, int_id))
    except MySQLdb.IntegrityError as e:
      raise db.UnknownClientError(client.client_id, cause=e)
    finally:
      client.startup_info = startup_info

  @mysql_utils.WithTransaction(readonly=True)
  def MultiReadClientSnapshot(self, client_ids, cursor=None):
    """Reads the latest client snapshots for a list of clients."""
    int_ids = [mysql_utils.ClientIDToInt(cid) for cid in client_ids]
    query = (
        "SELECT h.client_id, h.client_snapshot, h.timestamp, s.startup_info "
        "FROM clients as c, client_snapshot_history as h, "
        "client_startup_history as s "
        "WHERE h.client_id = c.client_id "
        "AND s.client_id = c.client_id "
        "AND h.timestamp = c.last_client_timestamp "
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
      client_obj.timestamp = mysql_utils.MysqlToRDFDatetime(timestamp)
      ret[mysql_utils.IntToClientID(cid)] = client_obj
    return ret

  @mysql_utils.WithTransaction(readonly=True)
  def ReadClientSnapshotHistory(self, client_id, timerange=None, cursor=None):
    """Reads the full history for a particular client."""

    client_id_int = mysql_utils.ClientIDToInt(client_id)

    query = ("SELECT sn.client_snapshot, st.startup_info, sn.timestamp FROM "
             "client_snapshot_history AS sn, "
             "client_startup_history AS st WHERE "
             "sn.client_id = st.client_id AND "
             "sn.timestamp = st.timestamp AND "
             "sn.client_id=%s ")

    args = [client_id_int]
    if timerange:
      time_from, time_to = timerange  # pylint: disable=unpacking-non-sequence

      if time_from is not None:
        query += "AND sn.timestamp >= %s "
        args.append(mysql_utils.RDFDatetimeToMysqlString(time_from))

      if time_to is not None:
        query += "AND sn.timestamp <= %s "
        args.append(mysql_utils.RDFDatetimeToMysqlString(time_to))

    query += "ORDER BY sn.timestamp DESC"

    ret = []
    cursor.execute(query, args)
    for snapshot, startup_info, timestamp in cursor.fetchall():
      client = rdf_objects.ClientSnapshot.FromSerializedString(snapshot)
      client.startup_info = rdf_client.StartupInfo.FromSerializedString(
          startup_info)
      client.timestamp = mysql_utils.MysqlToRDFDatetime(timestamp)

      ret.append(client)
    return ret

  @mysql_utils.WithTransaction()
  def WriteClientSnapshotHistory(self, clients, cursor=None):
    """Writes the full history for a particular client."""
    cid = mysql_utils.ClientIDToInt(clients[0].client_id)
    latest_timestamp = None

    for client in clients:

      startup_info = client.startup_info
      client.startup_info = None
      timestamp = mysql_utils.RDFDatetimeToMysqlString(client.timestamp)
      latest_timestamp = max(latest_timestamp, client.timestamp)

      try:
        cursor.execute(
            "INSERT INTO client_snapshot_history "
            "(client_id, timestamp, client_snapshot) "
            "VALUES (%s, %s, %s)",
            [cid, timestamp, client.SerializeToString()])
        cursor.execute(
            "INSERT INTO client_startup_history "
            "(client_id, timestamp, startup_info) "
            "VALUES (%s, %s, %s)",
            [cid, timestamp, startup_info.SerializeToString()])
      except MySQLdb.IntegrityError as e:
        raise db.UnknownClientError(clients[0].client_id, cause=e)
      finally:
        client.startup_info = startup_info

    latest_timestamp_str = mysql_utils.RDFDatetimeToMysqlString(
        latest_timestamp)
    cursor.execute(
        "UPDATE clients SET last_client_timestamp=%s "
        "WHERE client_id = %s AND "
        "(last_client_timestamp IS NULL OR last_client_timestamp < %s)",
        [latest_timestamp_str, cid, latest_timestamp_str])
    cursor.execute(
        "UPDATE clients SET last_startup_timestamp=%s "
        "WHERE client_id = %s AND "
        "(last_startup_timestamp IS NULL OR last_startup_timestamp < %s)",
        [latest_timestamp_str, cid, latest_timestamp_str])

  @mysql_utils.WithTransaction()
  def WriteClientStartupInfo(self, client_id, startup_info, cursor=None):
    """Writes a new client startup record."""
    cid = mysql_utils.ClientIDToInt(client_id)
    now = mysql_utils.RDFDatetimeToMysqlString(rdfvalue.RDFDatetime.Now())

    try:
      cursor.execute(
          "INSERT INTO client_startup_history "
          "(client_id, timestamp, startup_info) "
          "VALUES (%s, %s, %s)",
          [cid, now, startup_info.SerializeToString()])
      cursor.execute(
          "UPDATE clients SET last_startup_timestamp = %s WHERE client_id=%s",
          [now, cid])
    except MySQLdb.IntegrityError as e:
      raise db.UnknownClientError(client_id, cause=e)

  @mysql_utils.WithTransaction(readonly=True)
  def ReadClientStartupInfo(self, client_id, cursor=None):
    """Reads the latest client startup record for a single client."""
    query = (
        "SELECT startup_info, timestamp FROM clients, client_startup_history "
        "WHERE clients.last_startup_timestamp=client_startup_history.timestamp "
        "AND clients.client_id=client_startup_history.client_id "
        "AND clients.client_id=%s")
    cursor.execute(query, [mysql_utils.ClientIDToInt(client_id)])
    row = cursor.fetchone()
    if row is None:
      return None

    startup_info, timestamp = row
    res = rdf_client.StartupInfo.FromSerializedString(startup_info)
    res.timestamp = mysql_utils.MysqlToRDFDatetime(timestamp)
    return res

  @mysql_utils.WithTransaction(readonly=True)
  def ReadClientStartupInfoHistory(self, client_id, timerange=None,
                                   cursor=None):
    """Reads the full startup history for a particular client."""

    client_id_int = mysql_utils.ClientIDToInt(client_id)

    query = ("SELECT startup_info, timestamp FROM client_startup_history "
             "WHERE client_id=%s ")
    args = [client_id_int]

    if timerange:
      time_from, time_to = timerange  # pylint: disable=unpacking-non-sequence

      if time_from is not None:
        query += "AND timestamp >= %s "
        args.append(mysql_utils.RDFDatetimeToMysqlString(time_from))

      if time_to is not None:
        query += "AND timestamp <= %s "
        args.append(mysql_utils.RDFDatetimeToMysqlString(time_to))

    query += "ORDER BY timestamp DESC "

    ret = []
    cursor.execute(query, args)

    for startup_info, timestamp in cursor.fetchall():
      si = rdf_client.StartupInfo.FromSerializedString(startup_info)
      si.timestamp = mysql_utils.MysqlToRDFDatetime(timestamp)
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
          yield mysql_utils.IntToClientID(prev_cid), c_full_info

        metadata = rdf_objects.ClientMetadata(
            certificate=crt,
            fleetspeak_enabled=fs,
            first_seen=mysql_utils.MysqlToRDFDatetime(first),
            ping=mysql_utils.MysqlToRDFDatetime(ping),
            clock=mysql_utils.MysqlToRDFDatetime(clk),
            ip=mysql_utils.StringToRDFProto(rdf_client_network.NetworkAddress,
                                            ip),
            last_foreman_time=mysql_utils.MysqlToRDFDatetime(foreman),
            startup_info_timestamp=mysql_utils.MysqlToRDFDatetime(
                last_startup_ts),
            last_crash_timestamp=mysql_utils.MysqlToRDFDatetime(last_crash_ts))

        if client_obj is not None:
          l_snapshot = rdf_objects.ClientSnapshot.FromSerializedString(
              client_obj)
          l_snapshot.timestamp = mysql_utils.MysqlToRDFDatetime(last_client_ts)
          l_snapshot.startup_info = rdf_client.StartupInfo.FromSerializedString(
              client_startup_obj)
          l_snapshot.startup_info.timestamp = l_snapshot.timestamp
        else:
          l_snapshot = rdf_objects.ClientSnapshot(
              client_id=mysql_utils.IntToClientID(cid))

        if last_startup_obj is not None:
          startup_info = rdf_client.StartupInfo.FromSerializedString(
              last_startup_obj)
          startup_info.timestamp = mysql_utils.MysqlToRDFDatetime(
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
      yield mysql_utils.IntToClientID(prev_cid), c_full_info

  @mysql_utils.WithTransaction(readonly=True)
  def MultiReadClientFullInfo(self, client_ids, min_last_ping=None,
                              cursor=None):
    """Reads full client information for a list of clients."""
    query = (
        "SELECT "
        "c.client_id, c.fleetspeak_enabled, c.certificate, c.last_ping, "
        "c.last_clock, c.last_ip, c.last_foreman, c.first_seen, "
        "c.last_client_timestamp, c.last_crash_timestamp, "
        "c.last_startup_timestamp, h.client_snapshot, s.startup_info, "
        "s_last.startup_info, l.owner, l.label "
        "FROM clients as c "
        "LEFT JOIN client_snapshot_history as h ON ( "
        "c.client_id = h.client_id AND h.timestamp = c.last_client_timestamp) "
        "LEFT JOIN client_startup_history as s ON ( "
        "c.client_id = s.client_id AND s.timestamp = c.last_client_timestamp) "
        "LEFT JOIN client_startup_history as s_last ON ( "
        "c.client_id = s_last.client_id "
        "AND s_last.timestamp = c.last_startup_timestamp) "
        "LEFT JOIN client_labels AS l ON (c.client_id = l.client_id) ")

    query += "WHERE c.client_id IN (%s) " % ", ".join(["%s"] * len(client_ids))

    values = [mysql_utils.ClientIDToInt(cid) for cid in client_ids]
    if min_last_ping is not None:
      query += "AND c.last_ping >= %s"
      values.append(mysql_utils.RDFDatetimeToMysqlString(min_last_ping))

    cursor.execute(query, values)
    ret = {}
    for c_id, c_info in self._ResponseToClientsFullInfo(cursor.fetchall()):
      ret[c_id] = c_info

    return ret

  @mysql_utils.WithTransaction(readonly=True)
  def ReadAllClientIDs(self, cursor=None):
    """Reads client ids for all clients in the database."""
    cursor.execute("SELECT client_id FROM clients")
    return [mysql_utils.IntToClientID(res[0]) for res in cursor.fetchall()]

  @mysql_utils.WithTransaction()
  def AddClientKeywords(self, client_id, keywords, cursor=None):
    """Associates the provided keywords with the client."""
    cid = mysql_utils.ClientIDToInt(client_id)
    now = datetime.datetime.utcnow()

    try:
      for kw in keywords:
        cursor.execute(
            "INSERT INTO client_keywords (client_id, keyword, timestamp) "
            "VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE timestamp=%s",
            [cid, utils.SmartUnicode(kw), now, now])
    except MySQLdb.IntegrityError as e:
      raise db.UnknownClientError(client_id, cause=e)

  @mysql_utils.WithTransaction()
  def RemoveClientKeyword(self, client_id, keyword, cursor=None):
    """Removes the association of a particular client to a keyword."""
    cursor.execute(
        "DELETE FROM client_keywords WHERE client_id=%s AND keyword=%s",
        [mysql_utils.ClientIDToInt(client_id),
         utils.SmartUnicode(keyword)])

  @mysql_utils.WithTransaction(readonly=True)
  def ListClientsForKeywords(self, keywords, start_time=None, cursor=None):
    """Lists the clients associated with keywords."""
    keywords = set(keywords)
    keyword_mapping = {utils.SmartUnicode(kw): kw for kw in keywords}

    result = {}
    for kw in itervalues(keyword_mapping):
      result[kw] = []

    query = ("SELECT DISTINCT keyword, client_id FROM client_keywords WHERE "
             "keyword IN ({})".format(",".join(["%s"] * len(keyword_mapping))))
    args = list(iterkeys(keyword_mapping))
    if start_time:
      query += " AND timestamp >= %s"
      args.append(mysql_utils.RDFDatetimeToMysqlString(start_time))

    cursor.execute(query, args)
    for kw, cid in cursor.fetchall():
      result[keyword_mapping[kw]].append(mysql_utils.IntToClientID(cid))
    return result

  @mysql_utils.WithTransaction()
  def AddClientLabels(self, client_id, owner, labels, cursor=None):
    """Attaches a list of user labels to a client."""
    cid = mysql_utils.ClientIDToInt(client_id)
    try:
      for label in labels:
        cursor.execute(
            "INSERT IGNORE INTO client_labels (client_id, owner, label) "
            "VALUES (%s, %s, %s)",
            [cid, owner, utils.SmartUnicode(label)])
    except MySQLdb.IntegrityError as e:
      raise db.UnknownClientError(client_id, cause=e)

  @mysql_utils.WithTransaction(readonly=True)
  def MultiReadClientLabels(self, client_ids, cursor=None):
    """Reads the user labels for a list of clients."""

    int_ids = [mysql_utils.ClientIDToInt(cid) for cid in client_ids]
    query = ("SELECT client_id, owner, label "
             "FROM client_labels "
             "WHERE client_id IN ({})").format(", ".join(
                 ["%s"] * len(client_ids)))

    ret = {client_id: [] for client_id in client_ids}
    cursor.execute(query, int_ids)
    for client_id, owner, label in cursor.fetchall():
      ret[mysql_utils.IntToClientID(client_id)].append(
          rdf_objects.ClientLabel(name=utils.SmartUnicode(label), owner=owner))

    for r in itervalues(ret):
      r.sort(key=lambda label: (label.owner, label.name))
    return ret

  @mysql_utils.WithTransaction()
  def RemoveClientLabels(self, client_id, owner, labels, cursor=None):
    """Removes a list of user labels from a given client."""

    query = ("DELETE FROM client_labels "
             "WHERE client_id=%s AND owner=%s "
             "AND label IN ({})").format(", ".join(["%s"] * len(labels)))
    args = [mysql_utils.ClientIDToInt(client_id), owner]
    args += [utils.SmartStr(l) for l in labels]
    cursor.execute(query, args)

  @mysql_utils.WithTransaction(readonly=True)
  def ReadAllClientLabels(self, cursor=None):
    """Reads the user labels for a list of clients."""

    cursor.execute("SELECT DISTINCT owner, label FROM client_labels")

    result = []
    for owner, label in cursor.fetchall():
      result.append(
          rdf_objects.ClientLabel(name=utils.SmartUnicode(label), owner=owner))

    result.sort(key=lambda label: (label.owner, label.name))
    return result

  @mysql_utils.WithTransaction()
  def WriteClientCrashInfo(self, client_id, crash_info, cursor=None):
    """Writes a new client crash record."""
    cid = mysql_utils.ClientIDToInt(client_id)
    now = mysql_utils.RDFDatetimeToMysqlString(rdfvalue.RDFDatetime.Now())
    try:
      cursor.execute(
          "INSERT INTO client_crash_history (client_id, timestamp, crash_info) "
          "VALUES (%s, %s, %s)",
          [cid, now, crash_info.SerializeToString()])
      cursor.execute(
          "UPDATE clients SET last_crash_timestamp = %s WHERE client_id=%s",
          [now, cid])

    except MySQLdb.IntegrityError as e:
      raise db.UnknownClientError(client_id, cause=e)

  @mysql_utils.WithTransaction(readonly=True)
  def ReadClientCrashInfo(self, client_id, cursor=None):
    """Reads the latest client crash record for a single client."""
    cursor.execute(
        "SELECT timestamp, crash_info FROM clients, client_crash_history WHERE "
        "clients.client_id = client_crash_history.client_id AND "
        "clients.last_crash_timestamp = client_crash_history.timestamp AND "
        "clients.client_id = %s", [mysql_utils.ClientIDToInt(client_id)])
    row = cursor.fetchone()
    if not row:
      return None

    timestamp, crash_info = row
    res = rdf_client.ClientCrash.FromSerializedString(crash_info)
    res.timestamp = mysql_utils.MysqlToRDFDatetime(timestamp)
    return res

  @mysql_utils.WithTransaction(readonly=True)
  def ReadClientCrashInfoHistory(self, client_id, cursor=None):
    """Reads the full crash history for a particular client."""
    cursor.execute(
        "SELECT timestamp, crash_info FROM client_crash_history WHERE "
        "client_crash_history.client_id = %s "
        "ORDER BY timestamp DESC", [mysql_utils.ClientIDToInt(client_id)])
    ret = []
    for timestamp, crash_info in cursor.fetchall():
      ci = rdf_client.ClientCrash.FromSerializedString(crash_info)
      ci.timestamp = mysql_utils.MysqlToRDFDatetime(timestamp)
      ret.append(ci)
    return ret
