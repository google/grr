#!/usr/bin/env python
"""MySQL implementation of the GRR relational database abstraction.

See grr/server/db.py for interface.

"""
import contextlib
import datetime
import functools
import inspect
import logging
import math
import random
import time
import warnings
import MySQLdb

from grr.lib import rdfvalue
from grr.lib import utils
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


def _IntToApprovalID(approval_id):
  return "%016x" % approval_id


def _ApprovalIDToInt(approval_id):
  return int(approval_id, 16)


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


def _ResponseToApprovalsWithGrants(response):
  """Converts a generator with approval rows into ApprovalRequest objects."""
  prev_triplet = None
  cur_approval_request = None
  for (approval_id_int, approval_timestamp, approval_request_bytes,
       grantor_username, grant_timestamp) in response:

    cur_triplet = (approval_id_int, approval_timestamp, approval_request_bytes)

    if cur_triplet != prev_triplet:
      prev_triplet = cur_triplet

      if cur_approval_request:
        yield cur_approval_request

      cur_approval_request = _StringToRDFProto(objects.ApprovalRequest,
                                               approval_request_bytes)
      cur_approval_request.approval_id = _IntToApprovalID(approval_id_int)

    if grantor_username and grant_timestamp:
      cur_approval_request.grants.append(
          objects.ApprovalGrant(
              grantor_username=grantor_username,
              timestamp=_MysqlToRDFDatetime(grant_timestamp)))

  if cur_approval_request:
    yield cur_approval_request


# Maximum retry count:
_MAX_RETRY_COUNT = 5

# MySQL error codes:
_RETRYABLE_ERRORS = {
    1205,  # ER_LOCK_WAIT_TIMEOUT
    1213,  # ER_LOCK_DEADLOCK
    1637,  # ER_TOO_MANY_CONCURRENT_TRXS
}


def _IsRetryable(error):
  """Returns whether error is likely to be retryable."""
  if not isinstance(error, MySQLdb.OperationalError):
    return False
  if not error.args:
    return False
  code = error.args[0]
  return code in _RETRYABLE_ERRORS


class WithTransaction(object):
  """Decorator that provides a connection or cursor with transaction management.

  Every function decorated @WithTransaction will receive a named 'connection' or
  'cursor' argument.

  If the caller provides a value for the needed parameter, it will be passed
  through without change.

  Otherwise, a connection will be reserved from the pool, a transaction started,
  the decorated function will be called with the missing argument.

  Afterward, the transaction will be committed and the connection returned to
  the pool. Furthermore, if a retryable database error is raised during this
  process, the decorated function may be called again after a short delay.
  """

  def __init__(self, readonly=False):
    """Constructs a decorator.

    Args:
      readonly: Whether the decorated function only requires a readonly
        transaction. Has no effect when a connection is provided.
    """
    self.readonly = readonly

  def __call__(self, func):
    readonly = self.readonly

    takes_args = inspect.getargspec(func).args
    takes_connection = "connection" in takes_args
    takes_cursor = "cursor" in takes_args

    if takes_connection == takes_cursor:
      raise TypeError(
          "@WithTransaction requires a function to take exactly "
          "one of 'connection', 'cursor', got: %s" % str(takes_args))

    if takes_connection:

      @functools.wraps(func)
      def Decorated(self, *args, **kw):
        """A function decorated by WithTransaction to receive a connection."""
        connection = kw.get("connection", None)
        if connection:
          return func(self, *args, **kw)

        def Closure(connection):
          new_kw = kw.copy()
          new_kw["connection"] = connection
          return func(self, *args, **new_kw)

        return self._RunInTransaction(Closure, readonly)

      return Decorated

    @functools.wraps(func)
    def Decorated(self, *args, **kw):  # pylint: disable=function-redefined
      """A function decorated by WithTransaction to receive a cursor."""
      cursor = kw.get("cursor", None)
      if cursor:
        return func(self, *args, **kw)

      def Closure(connection):
        with contextlib.closing(connection.cursor()) as cursor:
          new_kw = kw.copy()
          new_kw["cursor"] = cursor
          return func(self, *args, **new_kw)

      return self._RunInTransaction(Closure, readonly)

    return Decorated


class MysqlDB(db_module.Database):
  """Implements db_module.Database using mysql.

  See server/db.py for a full description of the interface.
  """

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
          autocommit=False,
          use_unicode=True,
          charset="utf8")

    self.pool = mysql_pool.Pool(Connect)
    self._MariaDBCompatibility()
    self._InitializeSchema()

  def _CheckForMariaDB(self, cursor):
    """Checks if we are running against MariaDB."""
    for variable in ["version", "version_comment"]:
      cursor.execute("SHOW VARIABLES LIKE %s;", (variable,))
      version = cursor.fetchone()
      if version and "MariaDB" in version[1]:
        return True
    return False

  def _MariaDBCompatibility(self):
    # MariaDB introduced raising warnings when INSERT IGNORE
    # encounters duplicate keys. This flag disables this behavior for
    # consistency.
    with contextlib.closing(self.pool.get()) as connection:
      with contextlib.closing(connection.cursor()) as cursor:
        if self._CheckForMariaDB(cursor):
          cursor.execute("SET @@OLD_MODE = CONCAT(@@OLD_MODE, "
                         "',NO_DUP_KEY_WARNINGS_WITH_IGNORE');")

  def _InitializeSchema(self):
    """Initialize the database's schema."""
    with contextlib.closing(self.pool.get()) as connection:
      with contextlib.closing(connection.cursor()) as cursor:
        for command in mysql_ddl.SCHEMA_SETUP:
          try:
            cursor.execute(command)
          except Exception:
            logging.error("Failed to execute DDL: %s", command)
            raise

  def _RunInTransaction(self, function, readonly=False):
    """Runs function within a transaction.

    Allocates a connection, begins a transaction on it and passes the connection
    to function.

    If function finishes without raising, the transaction is committed.

    If function raises, the transaction will be rolled back, if a retryable
    database error is raised, the operation may be repeated.

    Args:
      function: A function to be run, must accept a single MySQLdb.connection
        parameter.
      readonly: Indicates that only a readonly (snapshot) transaction is
        required.

    Returns:
      The value returned by the last call to function.

    Raises: Any exception raised by function.
    """
    start_query = "START TRANSACTION;"
    if readonly:
      start_query = "START TRANSACTION WITH CONSISTENT SNAPSHOT, READ ONLY;"

    for retry_count in range(_MAX_RETRY_COUNT):
      with contextlib.closing(self.pool.get()) as connection:
        try:
          with contextlib.closing(connection.cursor()) as cursor:
            cursor.execute(start_query)

          ret = function(connection)

          if not readonly:
            connection.commit()
          return ret
        except MySQLdb.OperationalError as e:
          connection.rollback()
          # Re-raise if this was the last attempt.
          if retry_count >= _MAX_RETRY_COUNT or not _IsRetryable(e):
            raise
      # Simple delay, with jitter.
      #
      # TODO(user): Move to something more elegant, e.g. integrate a
      # general retry or backoff library.
      time.sleep(random.uniform(1.0, 2.0) * math.pow(1.5, retry_count))
    # Shouldn't happen, because we should have re-raised whatever caused the
    # last try to fail.
    raise Exception("Looped ended early - last exception swallowed.")  # pylint: disable=g-doc-exception

  @WithTransaction()
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
    cursor.execute(query, values)

  @WithTransaction(readonly=True)
  def MultiReadClientMetadata(self, client_ids, cursor=None):
    """Reads ClientMetadata records for a list of clients."""
    ids = [_ClientIDToInt(client_id) for client_id in client_ids]
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
      ret[_IntToClientID(cid)] = objects.ClientMetadata(
          certificate=crt,
          fleetspeak_enabled=fs,
          first_seen=_MysqlToRDFDatetime(first),
          ping=_MysqlToRDFDatetime(ping),
          clock=_MysqlToRDFDatetime(clk),
          ip=_StringToRDFProto(rdf_client.NetworkAddress, ip),
          last_foreman_time=_MysqlToRDFDatetime(foreman),
          startup_info_timestamp=_MysqlToRDFDatetime(lst),
          last_crash_timestamp=_MysqlToRDFDatetime(lct))
    return ret

  @WithTransaction()
  def WriteClientSnapshot(self, client, cursor=None):
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

    try:
      cursor.execute(insert_history_query,
                     (int_id, timestamp, client.SerializeToString()))
      cursor.execute(insert_startup_query,
                     (int_id, timestamp, startup_info.SerializeToString()))
      cursor.execute(update_query, (timestamp, timestamp, int_id))
    except MySQLdb.IntegrityError as e:
      raise db_module.UnknownClientError(e)
    finally:
      client.startup_info = startup_info

  @WithTransaction(readonly=True)
  def MultiReadClientSnapshot(self, client_ids, cursor=None):
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
    return ret

  @WithTransaction(readonly=True)
  def ReadClientSnapshotHistory(self, client_id, timerange=None, cursor=None):
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

    ret = []
    cursor.execute(query, args)
    for snapshot, startup_info, timestamp in cursor.fetchall():
      client = objects.ClientSnapshot.FromSerializedString(snapshot)
      client.startup_info = rdf_client.StartupInfo.FromSerializedString(
          startup_info)
      client.timestamp = _MysqlToRDFDatetime(timestamp)

      ret.append(client)
    return ret

  @WithTransaction()
  def WriteClientSnapshotHistory(self, clients, cursor=None):
    super(MysqlDB, self).WriteClientSnapshotHistory(clients)

    cid = _ClientIDToInt(clients[0].client_id)
    latest_timestamp = None

    for client in clients:

      startup_info = client.startup_info
      client.startup_info = None
      timestamp = _RDFDatetimeToMysqlString(client.timestamp)
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
        raise db_module.UnknownClientError(e)
      finally:
        client.startup_info = startup_info

    latest_timestamp_str = _RDFDatetimeToMysqlString(latest_timestamp)
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

  @WithTransaction()
  def WriteClientStartupInfo(self, client_id, startup_info, cursor=None):
    """Writes a new client startup record."""
    if not isinstance(startup_info, rdf_client.StartupInfo):
      raise ValueError(
          "WriteClientStartupInfo requires rdf_client.StartupInfo, got: %s" %
          type(startup_info))

    cid = _ClientIDToInt(client_id)
    now = _RDFDatetimeToMysqlString(rdfvalue.RDFDatetime.Now())

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
      raise db_module.UnknownClientError(e)

  @WithTransaction(readonly=True)
  def ReadClientStartupInfo(self, client_id, cursor=None):
    query = (
        "SELECT startup_info, timestamp FROM clients, client_startup_history "
        "WHERE clients.last_startup_timestamp=client_startup_history.timestamp "
        "AND clients.client_id=client_startup_history.client_id "
        "AND clients.client_id=%s")
    cursor.execute(query, [_ClientIDToInt(client_id)])
    row = cursor.fetchone()
    if row is None:
      return None

    startup_info, timestamp = row
    res = rdf_client.StartupInfo.FromSerializedString(startup_info)
    res.timestamp = _MysqlToRDFDatetime(timestamp)
    return res

  @WithTransaction(readonly=True)
  def ReadClientStartupInfoHistory(self, client_id, timerange=None,
                                   cursor=None):

    client_id_int = _ClientIDToInt(client_id)

    query = ("SELECT startup_info, timestamp FROM client_startup_history "
             "WHERE client_id=%s ")
    args = [client_id_int]

    if timerange:
      time_from, time_to = timerange  # pylint: disable=unpacking-non-sequence

      if time_from is not None:
        query += "AND timestamp >= %s "
        args.append(_RDFDatetimeToMysqlString(time_from))

      if time_to is not None:
        query += "AND timestamp <= %s "
        args.append(_RDFDatetimeToMysqlString(time_to))

    query += "ORDER BY timestamp DESC "

    ret = []
    cursor.execute(query, args)

    for startup_info, timestamp in cursor.fetchall():
      si = rdf_client.StartupInfo.FromSerializedString(startup_info)
      si.timestamp = _MysqlToRDFDatetime(timestamp)
      ret.append(si)
    return ret

  def _ResponseToClientsFullInfo(self, response):
    c_full_info = None
    prev_cid = None
    for row in response:
      (cid, fs, crt, ping, clk, ip, foreman, first, last_client_ts,
       last_crash_ts, last_startup_ts, client_obj, client_startup_obj,
       last_startup_obj, label_owner, label_name) = row

      if cid != prev_cid:
        if c_full_info:
          yield _IntToClientID(prev_cid), c_full_info

        metadata = objects.ClientMetadata(
            certificate=crt,
            fleetspeak_enabled=fs,
            first_seen=_MysqlToRDFDatetime(first),
            ping=_MysqlToRDFDatetime(ping),
            clock=_MysqlToRDFDatetime(clk),
            ip=_StringToRDFProto(rdf_client.NetworkAddress, ip),
            last_foreman_time=_MysqlToRDFDatetime(foreman),
            startup_info_timestamp=_MysqlToRDFDatetime(last_startup_ts),
            last_crash_timestamp=_MysqlToRDFDatetime(last_crash_ts))

        if client_obj is not None:
          l_snapshot = objects.ClientSnapshot.FromSerializedString(client_obj)
          l_snapshot.timestamp = _MysqlToRDFDatetime(last_client_ts)
          l_snapshot.startup_info = rdf_client.StartupInfo.FromSerializedString(
              client_startup_obj)
          l_snapshot.startup_info.timestamp = l_snapshot.timestamp
        else:
          l_snapshot = objects.ClientSnapshot(client_id=_IntToClientID(cid))

        if last_startup_obj is not None:
          startup_info = rdf_client.StartupInfo.FromSerializedString(
              last_startup_obj)
          startup_info.timestamp = _MysqlToRDFDatetime(last_startup_ts)
        else:
          startup_info = None

        prev_cid = cid
        c_full_info = objects.ClientFullInfo(
            metadata=metadata,
            labels=[],
            last_snapshot=l_snapshot,
            last_startup_info=startup_info)

      if label_owner and label_name:
        c_full_info.labels.append(
            objects.ClientLabel(name=label_name, owner=label_owner))

    if c_full_info:
      yield _IntToClientID(prev_cid), c_full_info

  @WithTransaction(readonly=True)
  def MultiReadClientFullInfo(self, client_ids, min_last_ping=None,
                              cursor=None):
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

    values = [_ClientIDToInt(cid) for cid in client_ids]
    if min_last_ping is not None:
      query += "AND c.last_ping >= %s"
      values.append(_RDFDatetimeToMysqlString(min_last_ping))

    cursor.execute(query, values)
    ret = {}
    for c_id, c_info in self._ResponseToClientsFullInfo(cursor.fetchall()):
      ret[c_id] = c_info

    return ret

  @WithTransaction(readonly=True)
  def ReadAllClientsID(self, cursor=None):
    """Reads client ids for all clients in the database."""
    cursor.execute("SELECT client_id FROM clients")
    return [_IntToClientID(res[0]) for res in cursor.fetchall()]

  @WithTransaction()
  def AddClientKeywords(self, client_id, keywords, cursor=None):
    """Associates the provided keywords with the client."""
    cid = _ClientIDToInt(client_id)
    now = datetime.datetime.utcnow()

    try:
      for kw in keywords:
        cursor.execute(
            "INSERT INTO client_keywords (client_id, keyword, timestamp) "
            "VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE timestamp=%s",
            [cid, utils.SmartUnicode(kw), now, now])
    except MySQLdb.IntegrityError as e:
      raise db_module.UnknownClientError(e)

  @WithTransaction()
  def RemoveClientKeyword(self, client_id, keyword, cursor=None):
    """Removes the association of a particular client to a keyword."""
    cursor.execute(
        "DELETE FROM client_keywords WHERE client_id=%s AND keyword=%s",
        [_ClientIDToInt(client_id),
         utils.SmartUnicode(keyword)])

  @WithTransaction(readonly=True)
  def ListClientsForKeywords(self, keywords, start_time=None, cursor=None):
    """Lists the clients associated with keywords."""
    keywords = set(keywords)
    keyword_mapping = {utils.SmartUnicode(kw): kw for kw in keywords}
    if len(keyword_mapping) != len(keywords):
      raise ValueError("Multiple keywords map to the same unicode "
                       "representation.")

    result = {}
    for kw in keyword_mapping.values():
      result[kw] = []

    query = ("SELECT DISTINCT keyword, client_id FROM client_keywords WHERE "
             "keyword IN ({})".format(",".join(["%s"] * len(keyword_mapping))))
    args = keyword_mapping.keys()
    if start_time:
      query += " AND timestamp >= %s"
      args.append(_RDFDatetimeToMysqlString(start_time))

    cursor.execute(query, args)
    for kw, cid in cursor.fetchall():
      result[keyword_mapping[kw]].append(_IntToClientID(cid))
    return result

  @WithTransaction()
  def AddClientLabels(self, client_id, owner, labels, cursor=None):
    """Attaches a list of user labels to a client."""
    cid = _ClientIDToInt(client_id)
    try:
      for label in labels:
        cursor.execute(
            "INSERT IGNORE INTO client_labels (client_id, owner, label) "
            "VALUES (%s, %s, %s)",
            [cid, owner, utils.SmartUnicode(label)])
    except MySQLdb.IntegrityError as e:
      raise db_module.UnknownClientError(e)

  @WithTransaction(readonly=True)
  def MultiReadClientLabels(self, client_ids, cursor=None):
    """Reads the user labels for a list of clients."""

    int_ids = [_ClientIDToInt(cid) for cid in client_ids]
    query = ("SELECT client_id, owner, label "
             "FROM client_labels "
             "WHERE client_id IN ({})").format(", ".join(
                 ["%s"] * len(client_ids)))

    ret = {client_id: [] for client_id in client_ids}
    cursor.execute(query, int_ids)
    for client_id, owner, label in cursor.fetchall():
      ret[_IntToClientID(client_id)].append(
          objects.ClientLabel(name=utils.SmartUnicode(label), owner=owner))

    for r in ret.values():
      r.sort(key=lambda label: (label.owner, label.name))
    return ret

  @WithTransaction()
  def RemoveClientLabels(self, client_id, owner, labels, cursor=None):
    """Removes a list of user labels from a given client."""

    query = ("DELETE FROM client_labels "
             "WHERE client_id=%s AND owner=%s "
             "AND label IN ({})").format(", ".join(["%s"] * len(labels)))
    args = [_ClientIDToInt(client_id), owner]
    args += [utils.SmartStr(l) for l in labels]
    cursor.execute(query, args)

  @WithTransaction(readonly=True)
  def ReadAllClientLabels(self, cursor=None):
    """Reads the user labels for a list of clients."""

    cursor.execute("SELECT DISTINCT owner, label FROM client_labels")

    result = []
    for owner, label in cursor.fetchall():
      result.append(
          objects.ClientLabel(name=utils.SmartUnicode(label), owner=owner))

    result.sort(key=lambda label: (label.owner, label.name))
    return result

  @WithTransaction()
  def WriteClientCrashInfo(self, client_id, crash_info, cursor=None):
    """Writes a new client crash record."""

    if not isinstance(crash_info, rdf_client.ClientCrash):
      raise ValueError(
          "WriteClientCrashInfo requires rdf_client.ClientCrash, got: %s" %
          type(crash_info))

    cid = _ClientIDToInt(client_id)
    now = _RDFDatetimeToMysqlString(rdfvalue.RDFDatetime.Now())
    try:
      cursor.execute(
          "INSERT INTO client_crash_history (client_id, timestamp, crash_info) "
          "VALUES (%s, %s, %s)",
          [cid, now, crash_info.SerializeToString()])
      cursor.execute(
          "UPDATE clients SET last_crash_timestamp = %s WHERE client_id=%s",
          [now, cid])

    except MySQLdb.IntegrityError as e:
      raise db_module.UnknownClientError(e)

  @WithTransaction(readonly=True)
  def ReadClientCrashInfo(self, client_id, cursor=None):
    cursor.execute(
        "SELECT timestamp, crash_info FROM clients, client_crash_history WHERE "
        "clients.client_id = client_crash_history.client_id AND "
        "clients.last_crash_timestamp = client_crash_history.timestamp AND "
        "clients.client_id = %s", [_ClientIDToInt(client_id)])
    row = cursor.fetchone()
    if not row:
      return None

    timestamp, crash_info = row
    res = rdf_client.ClientCrash.FromSerializedString(crash_info)
    res.timestamp = _MysqlToRDFDatetime(timestamp)
    return res

  @WithTransaction(readonly=True)
  def ReadClientCrashInfoHistory(self, client_id, cursor=None):
    cursor.execute(
        "SELECT timestamp, crash_info FROM client_crash_history WHERE "
        "client_crash_history.client_id = %s "
        "ORDER BY timestamp DESC", [_ClientIDToInt(client_id)])
    ret = []
    for timestamp, crash_info in cursor.fetchall():
      ci = rdf_client.ClientCrash.FromSerializedString(crash_info)
      ci.timestamp = _MysqlToRDFDatetime(timestamp)
      ret.append(ci)
    return ret

  @WithTransaction()
  def WriteGRRUser(self,
                   username,
                   password=None,
                   ui_mode=None,
                   canary_mode=None,
                   user_type=None,
                   cursor=None):

    columns = ["username"]
    values = [username]

    if password is not None:
      columns.append("password")
      values.append(password.SerializeToString())
    if ui_mode is not None:
      columns.append("ui_mode")
      values.append(int(ui_mode))
    if canary_mode is not None:
      columns.append("canary_mode")
      # TODO(amoser): This int conversion is dirty but necessary with
      # the current MySQL driver.
      values.append(int(bool(canary_mode)))
    if user_type is not None:
      columns.append("user_type")
      values.append(int(user_type))

    query = "INSERT INTO grr_users ({cols}) VALUES ({vals})".format(
        cols=", ".join(columns), vals=", ".join(["%s"] * len(columns)))

    if len(values) > 1:
      updates = ", ".join(
          ["{c} = VALUES ({c})".format(c=col) for col in columns[1:]])
      query += "ON DUPLICATE KEY UPDATE " + updates

    cursor.execute(query, values)

  def _RowToGRRUser(self, row):
    username, password, ui_mode, canary_mode, user_type = row
    result = objects.GRRUser(
        username=username,
        ui_mode=ui_mode,
        canary_mode=canary_mode,
        user_type=user_type)

    if password:
      result.password.ParseFromString(password)

    return result

  @WithTransaction(readonly=True)
  def ReadGRRUser(self, username, cursor=None):

    cursor.execute(
        "SELECT username, password, ui_mode, canary_mode, user_type "
        "FROM grr_users WHERE username=%s", [username])

    row = cursor.fetchone()
    if row is None:
      raise db_module.UnknownGRRUserError("User '%s' not found." % username)

    return self._RowToGRRUser(row)

  @WithTransaction(readonly=True)
  def ReadAllGRRUsers(self, cursor=None):
    cursor.execute("SELECT username, password, ui_mode, canary_mode, user_type "
                   "FROM grr_users")
    res = []
    for row in cursor.fetchall():
      res.append(self._RowToGRRUser(row))
    return res

  @WithTransaction()
  def WriteApprovalRequest(self, approval_request, cursor=None):
    """Writes an approval request object."""

    if not isinstance(approval_request, objects.ApprovalRequest):
      raise ValueError(
          "WriteApprovalRequest requires rdfvalues.objects.ApprovalRequest, "
          "got: %s" % type(approval_request))

    # Copy the approval_request to ensure we don't modify the source object.
    approval_request = approval_request.Copy()
    # Generate random approval id.
    approval_id_int = utils.PRNG.GetUInt64()
    now_str = _RDFDatetimeToMysqlString(rdfvalue.RDFDatetime.Now())

    grants = approval_request.grants
    approval_request.grants = None

    query = ("INSERT INTO approval_request (username, approval_type, "
             "subject_id, approval_id, timestamp, expiration_time, "
             "approval_request) VALUES (%s, %s, %s, %s, %s, %s, %s)")

    args = [
        approval_request.requestor_username,
        int(approval_request.approval_type), approval_request.subject_id,
        approval_id_int, now_str,
        _RDFDatetimeToMysqlString(approval_request.expiration_time),
        approval_request.SerializeToString()
    ]
    cursor.execute(query, args)

    for grant in grants:
      grant_query = ("INSERT INTO approval_grant (username, approval_id, "
                     "grantor_username, timestamp) VALUES (%s, %s, %s, %s)")
      grant_args = [
          approval_request.requestor_username, approval_id_int,
          grant.grantor_username, now_str
      ]
      cursor.execute(grant_query, grant_args)

    return _IntToApprovalID(approval_id_int)

  @WithTransaction()
  def GrantApproval(self,
                    requestor_username,
                    approval_id,
                    grantor_username,
                    cursor=None):
    """Grants approval for a given request using given username."""
    now_str = _RDFDatetimeToMysqlString(rdfvalue.RDFDatetime.Now())
    grant_query = ("INSERT INTO approval_grant (username, approval_id, "
                   "grantor_username, timestamp) VALUES (%s, %s, %s, %s)")
    grant_args = [
        requestor_username,
        _ApprovalIDToInt(approval_id), grantor_username, now_str
    ]
    cursor.execute(grant_query, grant_args)

  @WithTransaction(readonly=True)
  def ReadApprovalRequest(self, requestor_username, approval_id, cursor=None):
    """Reads an approval request object with a given id."""

    query = ("SELECT approval_request.approval_id, approval_request.timestamp, "
             "approval_request.approval_request, "
             "approval_grant.grantor_username, approval_grant.timestamp "
             "FROM approval_request "
             "LEFT JOIN approval_grant USING (username, approval_id) "
             "WHERE approval_request.approval_id=%s "
             "AND approval_request.username=%s")

    cursor.execute(query, [_ApprovalIDToInt(approval_id), requestor_username])
    res = cursor.fetchall()
    if not res:
      raise db_module.UnknownApprovalRequestError(
          "Approval '%s' not found." % approval_id)

    approval_id_int, timestamp, approval_request_bytes, _, _ = res[0]

    approval_request = _StringToRDFProto(objects.ApprovalRequest,
                                         approval_request_bytes)
    approval_request.approval_id = _IntToApprovalID(approval_id_int)
    approval_request.timestamp = _MysqlToRDFDatetime(timestamp)

    for _, _, _, grantor_username, timestamp in res:
      if not grantor_username:
        continue

      # Note: serialized approval_request objects are guaranteed to not
      # have any grants.
      approval_request.grants.append(
          objects.ApprovalGrant(
              grantor_username=grantor_username,
              timestamp=_MysqlToRDFDatetime(timestamp)))

    return approval_request

  @WithTransaction(readonly=True)
  def ReadApprovalRequests(self,
                           requestor_username,
                           approval_type,
                           subject_id=None,
                           include_expired=False,
                           cursor=None):
    """Reads approval requests of a given type for a given user."""

    query = ("SELECT ar.approval_id, ar.timestamp, ar.approval_request, "
             "ag.grantor_username, ag.timestamp "
             "FROM approval_request ar "
             "LEFT JOIN approval_grant AS ag USING (username, approval_id) "
             "WHERE ar.username=%s AND ar.approval_type=%s")

    args = [requestor_username, int(approval_type)]

    if subject_id:
      query += " AND ar.subject_id = %s"
      args.append(subject_id)

    query += " ORDER BY ar.approval_id"

    ret = []
    now = rdfvalue.RDFDatetime.Now()
    cursor.execute(query, args)
    for approval_request in _ResponseToApprovalsWithGrants(cursor.fetchall()):
      if include_expired or approval_request.expiration_time >= now:
        ret.append(approval_request)
    return ret

  def FindPathInfosByPathIDs(self, client_id, path_ids):
    """Returns path info records for a client."""
    raise NotImplementedError()

  def WritePathInfosRaw(self, client_id, path_infos):
    """Writes a collection of path_info records for a client."""
    raise NotImplementedError()

  def FindDescendentPathIDs(self, client_id, path_id, max_depth=None):
    """Finds all path_ids seen on a client descent from path_id."""
    raise NotImplementedError()
