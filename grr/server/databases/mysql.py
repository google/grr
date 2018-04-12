#!/usr/bin/env python
"""MySQL implementation of the GRR relational database abstraction.

See grr/server/db.py for interface.

"""
import datetime
import logging
import warnings
import MySQLdb

from grr.lib import rdfvalue
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import crypto as rdf_crypto
from grr.lib.rdfvalues import objects
from grr.server import db as db_module
from grr.server.databases import mysql_ddl
from grr.server.databases import mysql_pool


# GRR Client IDs are strings of the form "C.<16 hex digits>", our MySQL schema
# uses uint64 values.
def _ClientIDToInt(client_id):
  return int(client_id[2:], 16)


def _IntToClientID(client_id):
  return "C.%016x" % client_id


def _StringToRDFProto(proto_type, value):
  return value if value is None else proto_type.FromSerializedString(value)


# The MySQL driver accepts and returns Python datetime objects.
def _MysqlToRDFDatetime(dt):
  return dt if dt is None else rdfvalue.RDFDatetime.FromDatetime(dt)


def _RDFDatetimeToMysqlString(rdf):
  if rdf is None:
    return None
  if not isinstance(rdf, rdfvalue.RDFDatetime):
    raise ValueError(
        "time value must be rdfvalue.RDFDatetime, got: %s" % type(rdf))
  return "%s.%06d" % (rdf, rdf.AsMicrosecondsSinceEpoch() % 1000000)


class MysqlDB(object):
  """Implements db_module.Database using mysql.

  See server/db.py for a full description of the interface.
  """

  # TODO(user): Inherit from Database (in server/db.py) once the
  # implementation is complete.

  def __init__(self, host=None, port=None, user=None, passwd=None, db=None):
    """Creates a datastore implementation.

    Args:
      host: Passed to MySQLdb.Connect when creating a new connection.
      port: Passed to MySQLdb.Connect when creating a new connection.
      user: Passed to MySQLdb.Connect when creating a new connection.
      passwd: Passed to MySQLdb.Connect when creating a new connection.
      db: Passed to MySQLdb.Connect when creating a new connection.
    """

    # Turn all SQL warnings into exceptions.
    warnings.filterwarnings("error", category=MySQLdb.Warning)

    def Connect():
      return MySQLdb.Connect(
          host=host,
          port=port,
          user=user,
          passwd=passwd,
          db=db,
          autocommit=False)

    self.pool = mysql_pool.Pool(Connect)
    self._InitializeSchema()

  def _InitializeSchema(self):
    """Initialize the database's schema."""
    connection = self.pool.get()
    cursor = connection.cursor()
    for command in mysql_ddl.SCHEMA_SETUP:
      try:
        cursor.execute(command)
      except Exception:
        logging.error("Failed to execute DDL: %s", command)
        raise
    cursor.close()
    connection.close()

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

    columns = ["client_id"]
    values = [_ClientIDToInt(client_id)]
    if certificate:
      columns.append("certificate")
      if not isinstance(certificate, rdf_crypto.RDFX509Cert):
        raise ValueError("certificate must be rdf_crypto.RDFX509Cert, got: %s" %
                         type(certificate))
      values.append(certificate.SerializeToString())
    if fleetspeak_enabled is not None:
      columns.append("fleetspeak_enabled")
      values.append(int(fleetspeak_enabled))
    if first_seen:
      columns.append("first_seen")
      values.append(_RDFDatetimeToMysqlString(first_seen))
    if last_ping:
      columns.append("last_ping")
      values.append(_RDFDatetimeToMysqlString(last_ping))
    if last_clock:
      columns.append("last_clock")
      values.append(_RDFDatetimeToMysqlString(last_clock))
    if last_ip:
      columns.append("last_ip")
      if not isinstance(last_ip, rdf_client.NetworkAddress):
        raise ValueError(
            "last_ip must be client.NetworkAddress, got: %s" % type(last_ip))
      values.append(last_ip.SerializeToString())
    if last_foreman:
      columns.append("last_foreman")
      values.append(_RDFDatetimeToMysqlString(last_foreman))

    query = ("INSERT INTO clients ({cols}) VALUES ({vals}) "
             "ON DUPLICATE KEY UPDATE {updates}").format(
                 cols=", ".join(columns),
                 vals=", ".join(["%s"] * len(columns)),
                 updates=", ".join([
                     "{c} = VALUES ({c})".format(c=col) for col in columns[1:]
                 ]))

    con = self.pool.get()
    cursor = con.cursor()
    try:
      cursor.execute(query, values)
      con.commit()
    finally:
      cursor.close()
      con.close()

  def MultiReadClientMetadata(self, client_ids):
    """Reads ClientMetadata records for a list of clients."""
    ids = [_ClientIDToInt(client_id) for client_id in client_ids]
    query = ("SELECT client_id, fleetspeak_enabled, certificate, last_ping, "
             "last_clock, last_ip, last_foreman, first_seen FROM "
             "clients WHERE client_id IN ({})").format(", ".join(
                 ["%s"] * len(ids)))
    con = self.pool.get()
    cursor = con.cursor()
    ret = {}
    try:
      cursor.execute(query, ids)
      while True:
        row = cursor.fetchone()
        if not row:
          break
        cid, fs, crt, ping, clk, ip, foreman, first = row
        ret[_IntToClientID(cid)] = objects.ClientMetadata(
            certificate=crt,
            fleetspeak_enabled=fs,
            first_seen=_MysqlToRDFDatetime(first),
            ping=_MysqlToRDFDatetime(ping),
            clock=_MysqlToRDFDatetime(clk),
            ip=_StringToRDFProto(rdf_client.NetworkAddress, ip),
            last_foreman_time=_MysqlToRDFDatetime(foreman))
    finally:
      cursor.close()
      con.close()
    return ret

  def WriteClientSnapshot(self, client):
    """Write new client snapshot."""

    if not isinstance(client, objects.ClientSnapshot):
      raise ValueError(
          "WriteClient requires rdfvalues.objects.ClientSnapshot, got: %s" %
          type(client))

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

    int_id = _ClientIDToInt(client.client_id)
    timestamp = datetime.datetime.utcnow()

    con = self.pool.get()
    cursor = con.cursor()
    try:
      cursor.execute(insert_history_query,
                     (int_id, timestamp, client.SerializeToString()))
      cursor.execute(insert_startup_query,
                     (int_id, timestamp, startup_info.SerializeToString()))
      cursor.execute(update_query, (timestamp, timestamp, int_id))
      con.commit()
    except MySQLdb.IntegrityError as e:
      raise db_module.UnknownClientError(str(e))
    finally:
      cursor.close()
      con.close()
      client.startup_info = startup_info

  # TODO(amoser): Inherit from db.Database instead.
  def ReadClientSnapshot(self, client_id):
    return self.MultiReadClientSnapshot([client_id])[client_id]

  def MultiReadClientSnapshot(self, client_ids):
    """Reads the latest client snapshots for a list of clients."""
    int_ids = [_ClientIDToInt(cid) for cid in client_ids]
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
    con = self.pool.get()
    cursor = con.cursor()
    try:
      cursor.execute(query, int_ids)
      while True:
        row = cursor.fetchone()
        if not row:
          break
        cid, snapshot, timestamp, startup_info = row
        client_obj = _StringToRDFProto(objects.ClientSnapshot, snapshot)
        client_obj.startup_info = _StringToRDFProto(rdf_client.StartupInfo,
                                                    startup_info)
        client_obj.timestamp = _MysqlToRDFDatetime(timestamp)
        ret[_IntToClientID(cid)] = client_obj
    finally:
      cursor.close()
      con.close()
    return ret

  def ReadClientSnapshotHistory(self, client_id, timerange=None):
    """Reads the full history for a particular client."""

    client_id_int = _ClientIDToInt(client_id)

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
        args.append(_RDFDatetimeToMysqlString(time_from))

      if time_to is not None:
        query += "AND sn.timestamp <= %s "
        args.append(_RDFDatetimeToMysqlString(time_to))

    query += "ORDER BY sn.timestamp DESC"

    con = self.pool.get()
    cursor = con.cursor()
    ret = []
    try:
      cursor.execute(query, args)
      while True:
        row = cursor.fetchone()
        if not row:
          break
        snapshot, startup_info, timestamp = row
        client = objects.ClientSnapshot.FromSerializedString(snapshot)
        client.startup_info = rdf_client.StartupInfo.FromSerializedString(
            startup_info)
        client.timestamp = _MysqlToRDFDatetime(timestamp)

        ret.append(client)
    finally:
      cursor.close()
      con.close()
    return ret

  def ReadAllClientsID(self):
    """Reads client ids for all clients in the database."""
    ret = []
    con = self.pool.get()
    cursor = con.cursor()

    try:
      cursor.execute("SELECT client_id FROM clients")
      while True:
        row = cursor.fetchone()
        if not row:
          break
        cid, = row
        ret.append(_IntToClientID(cid))
      return ret
    finally:
      cursor.close()
      con.close()
