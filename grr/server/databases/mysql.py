#!/usr/bin/env python
"""MySQL implementation of the GRR relational database abstraction.

See grr/server/db.py for interface.

"""
import logging
import MySQLdb

from grr.lib import rdfvalue
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import crypto as rdf_crypto
from grr.lib.rdfvalues import objects
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


def _RDFDatetimeToMysql(rdf):
  if rdf is None:
    return None
  if not isinstance(rdf, rdfvalue.RDFDatetime):
    raise ValueError(
        "time value must be rdfvalue.RDFDatetime, got: %s" % type(rdf))
  return rdf.AsDatetime()


class MysqlDB(object):
  """Implements db.Database using mysql.

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

    def Connect():
      return MySQLdb.Connect(
          host=host, port=port, user=user, passwd=passwd, db=db)

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
      values.append(_RDFDatetimeToMysql(first_seen))
    if last_ping:
      columns.append("last_ping")
      values.append(_RDFDatetimeToMysql(last_ping))
    if last_clock:
      columns.append("last_clock")
      values.append(_RDFDatetimeToMysql(last_clock))
    if last_ip:
      columns.append("last_ip")
      if not isinstance(last_ip, rdf_client.NetworkAddress):
        raise ValueError(
            "last_ip must be client.NetworkAddress, got: %s" % type(last_ip))
      values.append(last_ip.SerializeToString())
    if last_foreman:
      columns.append("last_foreman")
      values.append(_RDFDatetimeToMysql(last_foreman))

    query = (
        "INSERT INTO clients ({cols}) VALUES ({vals}) ON DUPLICATE KEY UPDATE "
        "{updates}").format(
            cols=", ".join(columns),
            vals=", ".join(["%s"] * len(columns)),
            updates=", ".join(
                ["%s = VALUES (%s)" % (col, col) for col in columns[1:]]))
    con = self.pool.get()
    cursor = con.cursor()
    try:
      cursor.execute(query, values)
      con.commit()
    finally:
      cursor.close()
      con.close()

  def ReadClientMetadatas(self, client_ids):
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
