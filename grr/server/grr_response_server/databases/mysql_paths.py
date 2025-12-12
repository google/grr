#!/usr/bin/env python
"""The MySQL database methods for path handling."""
from collections.abc import Collection, Iterable, Sequence
from typing import Optional

import MySQLdb

from grr_response_core.lib import rdfvalue
from grr_response_proto import objects_pb2
from grr_response_server.databases import db
from grr_response_server.databases import db_utils
from grr_response_server.databases import mysql_utils
from grr_response_server.models import paths as models_paths
from grr_response_server.rdfvalues import objects as rdf_objects


class MySQLDBPathMixin(object):
  """MySQLDB mixin for path related functions."""

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction(readonly=True)
  def ReadPathInfo(
      self,
      client_id: str,
      path_type: objects_pb2.PathInfo.PathType,
      components: Sequence[str],
      timestamp: Optional[rdfvalue.RDFDatetime] = None,
      cursor: Optional[MySQLdb.cursors.Cursor] = None,
  ) -> objects_pb2.PathInfo:
    """Retrieves a path info record for a given path."""
    assert cursor is not None

    if timestamp is None:
      path_infos = self.ReadPathInfos(client_id, path_type, [components])

      path_info = path_infos[tuple(components)]
      if path_info is None:
        raise db.UnknownPathError(
            client_id=client_id, path_type=path_type, components=components
        )
      return path_info

    # If/when support for MySQL 5.x is dropped, this query can be cleaned up
    # with a common table expression (CTE).
    # The joining below is just a way to run multiple (independent) queries in a
    # single go, and merge their results. We are doing multiple selects over a
    # single unique key (client_id, path_type, path_id). This can be expressed
    # more cleanly with a CTE:
    #
    # ```
    # WITH
    #   stat_entry AS (SELECT stat_entry FROM ...
    #     WHERE timestamp < %(timestamp)s ... LIMIT 1),
    #   last_stat_entry_timestamp AS (SELECT timestamp FROM ...
    #     WHERE ... ORDER BY timestamp DESC LIMIT 1)
    #   ...
    # SELECT stat_entry, last_stat_entry_timestamp, ...
    # FROM client_paths
    # WHERE ...
    # ```
    query = """
    SELECT p.directory, UNIX_TIMESTAMP(p.timestamp),
           s.stat_entry, UNIX_TIMESTAMP(ls.timestamp),
           h.hash_entry, UNIX_TIMESTAMP(lh.timestamp)
      FROM client_paths as p
 LEFT JOIN (SELECT stat_entry
              FROM client_path_stat_entries
             WHERE (client_id, path_type, path_id) =
                   (%(client_id)s, %(path_type)s, %(path_id)s)
               AND UNIX_TIMESTAMP(timestamp) <= %(timestamp)s
          ORDER BY timestamp DESC
             LIMIT 1) AS s
        ON TRUE
 LEFT JOIN (SELECT timestamp
              FROM client_path_stat_entries
             WHERE (client_id, path_type, path_id) =
                   (%(client_id)s, %(path_type)s, %(path_id)s)
          ORDER BY timestamp DESC
             LIMIT 1) AS ls
        ON TRUE
 LEFT JOIN (SELECT hash_entry
              FROM client_path_hash_entries
             WHERE (client_id, path_type, path_id) =
                   (%(client_id)s, %(path_type)s, %(path_id)s)
               AND UNIX_TIMESTAMP(timestamp) <= %(timestamp)s
          ORDER BY timestamp DESC
             LIMIT 1) AS h
        ON TRUE
 LEFT JOIN (SELECT timestamp
              FROM client_path_hash_entries
             WHERE (client_id, path_type, path_id) =
                   (%(client_id)s, %(path_type)s, %(path_id)s)
          ORDER BY timestamp DESC
             LIMIT 1) AS lh
        ON TRUE
     WHERE (p.client_id, p.path_type, p.path_id) =
           (%(client_id)s, %(path_type)s, %(path_id)s)
    """
    values = {
        "client_id": db_utils.ClientIDToInt(client_id),
        "path_type": int(path_type),
        "path_id": rdf_objects.PathID.FromComponents(components).AsBytes(),
        "timestamp": mysql_utils.RDFDatetimeToTimestamp(timestamp),
    }

    cursor.execute(query, values)
    row = cursor.fetchone()
    if row is None:
      raise db.UnknownPathError(
          client_id=client_id, path_type=path_type, components=components
      )

    # fmt: off
    (directory, timestamp,
     stat_entry_bytes, last_stat_entry_timestamp,
     hash_entry_bytes, last_hash_entry_timestamp) = row
    # fmt: on

    path_info = objects_pb2.PathInfo(
        path_type=objects_pb2.PathInfo.PathType.Name(path_type),
        components=components,
        directory=directory,
    )

    datetime = mysql_utils.TimestampToMicrosecondsSinceEpoch
    if timestamp is not None:
      path_info.timestamp = datetime(timestamp)
    if last_stat_entry_timestamp is not None:
      path_info.last_stat_entry_timestamp = datetime(last_stat_entry_timestamp)
    if last_hash_entry_timestamp is not None:
      path_info.last_hash_entry_timestamp = datetime(last_hash_entry_timestamp)

    if stat_entry_bytes is not None:
      path_info.stat_entry.ParseFromString(stat_entry_bytes)
    if hash_entry_bytes is not None:
      path_info.hash_entry.ParseFromString(hash_entry_bytes)

    return path_info

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction(readonly=True)
  def ReadPathInfos(
      self,
      client_id: str,
      path_type: objects_pb2.PathInfo.PathType,
      components_list: Collection[Sequence[str]],
      cursor: Optional[MySQLdb.cursors.Cursor] = None,
  ) -> dict[tuple[str, ...], Optional[objects_pb2.PathInfo]]:
    """Retrieves path info records for given paths."""
    assert cursor is not None

    if not components_list:
      return {}

    path_ids = list(map(rdf_objects.PathID.FromComponents, components_list))

    path_infos = {tuple(components): None for components in components_list}

    query = """
    SELECT p.path, p.directory, UNIX_TIMESTAMP(p.timestamp),
           ls.stat_entry, UNIX_TIMESTAMP(ls.timestamp),
           lh.hash_entry, UNIX_TIMESTAMP(lh.timestamp)
      FROM client_paths AS p
 LEFT JOIN client_path_stat_entries AS ls
        ON ls.id = (SELECT id
                      FROM client_path_stat_entries
                     WHERE (client_id, path_type, path_id) =
                           (p.client_id, p.path_type, p.path_id)
                  ORDER BY timestamp DESC
                     LIMIT 1)
 LEFT JOIN client_path_hash_entries AS lh
        ON lh.id = (SELECT id
                      FROM client_path_hash_entries
                     WHERE (client_id, path_type, path_id) =
                           (p.client_id, p.path_type, p.path_id)
                  ORDER BY timestamp DESC
                     LIMIT 1)
     WHERE p.client_id = %s
       AND p.path_type = %s
       AND p.path_id IN ({})
    """.format(", ".join(["%s"] * len(path_ids)))
    # NOTE: passing tuples as cursor.execute arguments is broken in
    # mysqldbclient==1.3.10
    # (see https://github.com/PyMySQL/mysqlclient-python/issues/145)
    # and is considered unmaintained.
    values = [
        db_utils.ClientIDToInt(client_id),
        int(path_type),
    ] + [path_id.AsBytes() for path_id in path_ids]

    cursor.execute(query, values)
    for row in cursor.fetchall():
      # fmt: off
      (path, directory, timestamp,
       stat_entry_bytes, last_stat_entry_timestamp,
       hash_entry_bytes, last_hash_entry_timestamp) = row
      # fmt: on

      components = mysql_utils.PathToComponents(path)
      path_info = objects_pb2.PathInfo(
          path_type=objects_pb2.PathInfo.PathType.Name(path_type),
          components=components,
          directory=directory,
      )

      datetime = mysql_utils.TimestampToMicrosecondsSinceEpoch
      if timestamp is not None:
        path_info.timestamp = datetime(timestamp)
      if last_stat_entry_timestamp is not None:
        path_info.last_stat_entry_timestamp = datetime(
            last_stat_entry_timestamp
        )
      if last_hash_entry_timestamp is not None:
        path_info.last_hash_entry_timestamp = datetime(
            last_hash_entry_timestamp
        )

      if stat_entry_bytes is not None:
        path_info.stat_entry.ParseFromString(stat_entry_bytes)
      if hash_entry_bytes is not None:
        path_info.hash_entry.ParseFromString(hash_entry_bytes)

      path_infos[tuple(components)] = path_info

    return path_infos

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction()
  def WritePathInfos(
      self,
      client_id: str,
      path_infos: Sequence[objects_pb2.PathInfo],
      cursor: Optional[MySQLdb.cursors.Cursor] = None,
  ) -> None:
    """Writes a collection of path_info records for a client."""
    assert cursor is not None
    now = mysql_utils.RDFDatetimeToTimestamp(rdfvalue.RDFDatetime.Now())

    int_client_id = db_utils.ClientIDToInt(client_id)

    # Since we need to validate client id even if there are no paths given, we
    # cannot rely on foreign key constraints and have to special-case this.
    if not path_infos:
      query = "SELECT client_id FROM clients WHERE client_id = %(client_id)s"
      cursor.execute(query, {"client_id": int_client_id})
      if not cursor.fetchall():
        raise db.UnknownClientError(client_id)

    path_info_values = []
    parent_path_info_values = []

    stat_entry_keys = []
    stat_entry_values = []

    hash_entry_keys = []
    hash_entry_values = []

    for path_info in path_infos:
      path = mysql_utils.ComponentsToPath(path_info.components)

      key = (
          int_client_id,
          int(path_info.path_type),
          rdf_objects.PathID.FromComponents(path_info.components).AsBytes(),
      )
      details = (
          now,
          path,
          bool(path_info.directory),
          len(path_info.components),
      )
      path_info_values.append(key + details)

      if path_info.HasField("stat_entry"):
        stat_entry_keys.extend(key)
        details = (now, path_info.stat_entry.SerializeToString())
        stat_entry_values.append(key + details)

      if path_info.HasField("hash_entry"):
        hash_entry_keys.extend(key)
        details = (
            now,
            path_info.hash_entry.SerializeToString(),
            path_info.hash_entry.sha256,
        )
        hash_entry_values.append(key + details)

      # TODO(hanuszczak): Implement a trie in order to avoid inserting
      # duplicated records.
      for parent_path_info in models_paths.GetAncestorPathInfos(path_info):
        path = mysql_utils.ComponentsToPath(parent_path_info.components)
        parent_key = (
            int_client_id,
            int(parent_path_info.path_type),
            rdf_objects.PathID.FromComponents(
                parent_path_info.components
            ).AsBytes(),
        )
        parent_details = (
            path,
            len(parent_path_info.components),
        )
        parent_path_info_values.append(parent_key + parent_details)

    if path_info_values:
      query = """
        INSERT INTO client_paths(client_id, path_type, path_id,
                                 timestamp,
                                 path, directory, depth)
        VALUES (%s, %s, %s, FROM_UNIXTIME(%s), %s, %s, %s)
        ON DUPLICATE KEY UPDATE
          timestamp = VALUES(timestamp),
          directory = directory OR VALUES(directory)
      """

      try:
        cursor.executemany(query, path_info_values)
      except MySQLdb.IntegrityError as error:
        raise db.UnknownClientError(client_id=client_id, cause=error)

    if parent_path_info_values:
      query = """
        INSERT INTO client_paths(client_id, path_type, path_id, path,
                                 directory, depth)
        VALUES (%s, %s, %s, %s, TRUE, %s)
        ON DUPLICATE KEY UPDATE
          directory = TRUE,
          timestamp = NOW(6)
      """
      cursor.executemany(query, parent_path_info_values)

    if stat_entry_values:
      query = """
        INSERT INTO client_path_stat_entries(client_id, path_type, path_id,
                                             timestamp,
                                             stat_entry)
        VALUES (%s, %s, %s, FROM_UNIXTIME(%s), %s)
      """
      cursor.executemany(query, stat_entry_values)

    if hash_entry_values:
      query = """
        INSERT INTO client_path_hash_entries(client_id, path_type, path_id,
                                             timestamp,
                                             hash_entry, sha256)
        VALUES (%s, %s, %s, FROM_UNIXTIME(%s), %s, %s)
      """
      cursor.executemany(query, hash_entry_values)

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction(readonly=True)
  def ListDescendantPathInfos(
      self,
      client_id: str,
      path_type: objects_pb2.PathInfo.PathType,
      components: Sequence[str],
      timestamp: Optional[rdfvalue.RDFDatetime] = None,
      max_depth: Optional[int] = None,
      cursor: Optional[MySQLdb.cursors.Cursor] = None,
  ) -> Sequence[objects_pb2.PathInfo]:
    """Lists path info records that correspond to descendants of given path."""
    assert cursor is not None
    path_infos = []

    query = ""

    path = mysql_utils.ComponentsToPath(components)
    escaped_path = db_utils.EscapeWildcards(db_utils.EscapeBackslashes(path))
    values = {
        "client_id": db_utils.ClientIDToInt(client_id),
        "path_type": int(path_type),
        "escaped_path": escaped_path,
        "path": path,
    }

    # Hint: the difference between the below two queries is the data source used
    # to fetch the stat/hash entry details. `last_{stat,hash}_entry_timestamp`
    # will always be fetched from the latest stat/hash entry in the DB. However,
    # if a max timestamp is given, then the full stat/hash entry details will be
    # fetched from the latest entry only up to that timestamp.
    if timestamp is None:
      query += """
      SELECT path, directory, UNIX_TIMESTAMP(p.timestamp),
             ls.stat_entry, UNIX_TIMESTAMP(ls.timestamp),
             lh.hash_entry, UNIX_TIMESTAMP(lh.timestamp)
        FROM client_paths AS p
   LEFT JOIN client_path_stat_entries AS ls
          ON ls.id = (SELECT id
                       FROM client_path_stat_entries
                      WHERE (client_id, path_type, path_id) =
                            (p.client_id, p.path_type, p.path_id)
                   ORDER BY timestamp DESC
                      LIMIT 1)
   LEFT JOIN client_path_hash_entries AS lh
          ON lh.id = (SELECT id
                       FROM client_path_hash_entries
                      WHERE (client_id, path_type, path_id) =
                            (p.client_id, p.path_type, p.path_id)
                   ORDER BY timestamp DESC
                      LIMIT 1)
      """
      only_explicit = False
    else:
      query += """
      SELECT path, directory, UNIX_TIMESTAMP(p.timestamp),
             s.stat_entry, UNIX_TIMESTAMP(ls.timestamp),
             h.hash_entry, UNIX_TIMESTAMP(lh.timestamp)
        FROM client_paths AS p
   LEFT JOIN client_path_stat_entries AS ls
          ON ls.id = (SELECT id
                       FROM client_path_stat_entries
                      WHERE (client_id, path_type, path_id) =
                            (p.client_id, p.path_type, p.path_id)
                   ORDER BY timestamp DESC
                      LIMIT 1)
   LEFT JOIN client_path_hash_entries AS lh
          ON lh.id = (SELECT id
                       FROM client_path_hash_entries
                      WHERE (client_id, path_type, path_id) =
                            (p.client_id, p.path_type, p.path_id)
                   ORDER BY timestamp DESC
                      LIMIT 1)
   LEFT JOIN client_path_stat_entries AS s
          ON s.id = (SELECT id
                       FROM client_path_stat_entries
                      WHERE (client_id, path_type, path_id) =
                            (p.client_id, p.path_type, p.path_id)
                        AND UNIX_TIMESTAMP(timestamp) <= %(timestamp)s
                   ORDER BY timestamp DESC
                      LIMIT 1)
   LEFT JOIN client_path_hash_entries AS h
          ON h.id = (SELECT id
                       FROM client_path_hash_entries
                      WHERE (client_id, path_type, path_id) =
                            (p.client_id, p.path_type, p.path_id)
                        AND UNIX_TIMESTAMP(timestamp) <= %(timestamp)s
                   ORDER BY timestamp DESC
                      LIMIT 1)
      """
      values["timestamp"] = mysql_utils.RDFDatetimeToTimestamp(timestamp)
      only_explicit = True

    query += """
    WHERE p.client_id = %(client_id)s
      AND p.path_type = %(path_type)s
      AND (path LIKE CONCAT(%(escaped_path)s, '/%%') OR path = %(path)s)
    """

    if max_depth is not None:
      query += """
      AND depth <= %(depth)s
      """
      values["depth"] = len(components) + max_depth

    cursor.execute(query, values)
    for row in cursor.fetchall():
      # fmt: off
      (path, directory, timestamp,
       stat_entry_bytes, last_stat_entry_timestamp,
       hash_entry_bytes, last_hash_entry_timestamp) = row
      # fmt: on

      path_components = mysql_utils.PathToComponents(path)

      path_info = objects_pb2.PathInfo(
          path_type=objects_pb2.PathInfo.PathType.Name(path_type),
          components=path_components,
          directory=directory,
      )

      datetime = mysql_utils.TimestampToMicrosecondsSinceEpoch
      if timestamp is not None:
        path_info.timestamp = datetime(timestamp)
      if last_stat_entry_timestamp is not None:
        path_info.last_stat_entry_timestamp = datetime(
            last_stat_entry_timestamp
        )
      if last_hash_entry_timestamp is not None:
        path_info.last_hash_entry_timestamp = datetime(
            last_hash_entry_timestamp
        )

      if stat_entry_bytes is not None:
        path_info.stat_entry.ParseFromString(stat_entry_bytes)
      if hash_entry_bytes is not None:
        path_info.hash_entry.ParseFromString(hash_entry_bytes)

      path_infos.append(path_info)

    path_infos.sort(key=lambda _: tuple(_.components))

    # The first entry should be always the base directory itself unless it is a
    # root directory that was never collected.
    if not path_infos and components:
      raise db.UnknownPathError(client_id, path_type, components)

    if path_infos and not path_infos[0].directory:
      raise db.NotDirectoryPathError(client_id, path_type, components)

    path_infos = path_infos[1:]

    # For specific timestamp, we return information only about explicit paths
    # (paths that have associated stat or hash entry or have an ancestor that is
    # explicit).
    if not only_explicit:
      return path_infos

    explicit_path_infos = []
    has_explicit_ancestor = set()

    # This list is sorted according to the keys component, so by traversing it
    # in the reverse order we make sure that we process deeper paths first.
    for path_info in reversed(path_infos):
      path_components = tuple(path_info.components)

      if (
          path_info.HasField("stat_entry")
          or path_info.HasField("hash_entry")
          or path_components in has_explicit_ancestor
      ):
        explicit_path_infos.append(path_info)
        has_explicit_ancestor.add(path_components[:-1])

    # Since we collected explicit paths in reverse order, we need to reverse it
    # again to conform to the interface.
    return list(reversed(explicit_path_infos))

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction(readonly=True)
  def ReadPathInfosHistories(
      self,
      client_id: str,
      path_type: objects_pb2.PathInfo.PathType,
      components_list: Iterable[Sequence[str]],
      cutoff: Optional[rdfvalue.RDFDatetime] = None,
      cursor: Optional[MySQLdb.cursors.Cursor] = None,
  ) -> dict[tuple[str, ...], Sequence[objects_pb2.PathInfo]]:
    """Reads a collection of hash and stat entries for given paths."""
    assert cursor is not None

    # MySQL does not handle well empty `IN` clauses so we guard against that.
    if not components_list:
      return {}

    path_infos = {tuple(components): [] for components in components_list}

    path_id_components: dict[rdf_objects.PathID, tuple[str, ...]] = {}
    for components in components_list:
      path_id = rdf_objects.PathID.FromComponents(components)
      path_id_components[path_id] = tuple(components)

    params = {
        "client_id": db_utils.ClientIDToInt(client_id),
        "path_type": int(path_type),
    }
    for path_id in path_id_components:
      params["path_id_%s" % path_id.AsHexString()] = path_id.AsBytes()

    path_id_placeholders = ", ".join([
        "%(path_id_{})s".format(path_id.AsHexString())
        for path_id in path_id_components
    ])

    if cutoff is not None:
      stat_entry_timestamp_condition = """
      AND s.timestamp <= FROM_UNIXTIME(%(cutoff)s)
      """
      hash_entry_timestamp_condition = """
      AND h.timestamp <= FROM_UNIXTIME(%(cutoff)s)
      """
      params["cutoff"] = mysql_utils.RDFDatetimeToTimestamp(cutoff)
    else:
      stat_entry_timestamp_condition = ""
      hash_entry_timestamp_condition = ""

    # MySQL does not support full outer joins, so we emulate them with a union.
    query = """
    SELECT s.path_id, s.stat_entry, UNIX_TIMESTAMP(s.timestamp),
           h.path_id, h.hash_entry, UNIX_TIMESTAMP(h.timestamp)
      FROM client_path_stat_entries AS s
 LEFT JOIN client_path_hash_entries AS h
        ON s.client_id = h.client_id
       AND s.path_type = h.path_type
       AND s.path_id = h.path_id
       AND s.timestamp = h.timestamp
     WHERE s.client_id = %(client_id)s
       AND s.path_type = %(path_type)s
       AND s.path_id IN ({path_id_placeholders})
       {stat_entry_timestamp_condition}
     UNION
    SELECT s.path_id, s.stat_entry, UNIX_TIMESTAMP(s.timestamp),
           h.path_id, h.hash_entry, UNIX_TIMESTAMP(h.timestamp)
      FROM client_path_hash_entries AS h
 LEFT JOIN client_path_stat_entries AS s
        ON h.client_id = s.client_id
       AND h.path_type = s.path_type
       AND h.path_id = s.path_id
       AND h.timestamp = s.timestamp
     WHERE h.client_id = %(client_id)s
       AND h.path_type = %(path_type)s
       AND h.path_id IN ({path_id_placeholders})
       {hash_entry_timestamp_condition}
    """.format(
        stat_entry_timestamp_condition=stat_entry_timestamp_condition,
        hash_entry_timestamp_condition=hash_entry_timestamp_condition,
        path_id_placeholders=path_id_placeholders,
    )

    cursor.execute(query, params)
    for row in cursor.fetchall():
      # fmt: off
      (stat_entry_path_id_bytes, stat_entry_bytes, stat_entry_timestamp,
       hash_entry_path_id_bytes, hash_entry_bytes, hash_entry_timestamp) = row
      # fmt: on

      path_id_bytes = stat_entry_path_id_bytes or hash_entry_path_id_bytes
      path_id = rdf_objects.PathID.FromSerializedBytes(path_id_bytes)
      components: tuple[str, ...] = tuple(path_id_components[path_id])

      timestamp = stat_entry_timestamp or hash_entry_timestamp

      path_info = objects_pb2.PathInfo(
          path_type=objects_pb2.PathInfo.PathType.Name(path_type),
          components=components,
      )

      if timestamp is not None:
        path_info.timestamp = mysql_utils.TimestampToMicrosecondsSinceEpoch(
            timestamp
        )

      if stat_entry_bytes is not None:
        path_info.stat_entry.ParseFromString(stat_entry_bytes)
      if hash_entry_bytes is not None:
        path_info.hash_entry.ParseFromString(hash_entry_bytes)

      path_infos[components].append(path_info)

    for comps in components_list:
      path_infos[tuple(comps)].sort(key=lambda path_info: path_info.timestamp)

    return path_infos

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction(readonly=True)
  def ReadLatestPathInfosWithHashBlobReferences(
      self,
      client_paths: Collection[db.ClientPath],
      max_timestamp: Optional[rdfvalue.RDFDatetime] = None,
      cursor: Optional[MySQLdb.cursors.Cursor] = None,
  ) -> dict[db.ClientPath, Optional[objects_pb2.PathInfo]]:
    """Returns PathInfos that have corresponding HashBlobReferences."""
    assert cursor is not None
    path_infos = {client_path: None for client_path in client_paths}

    path_id_components = {}
    for client_path in client_paths:
      path_id_components[client_path.path_id] = client_path.components

    params = []
    query = """
    SELECT t.client_id, t.path_type, t.path_id, UNIX_TIMESTAMP(t.timestamp),
           s.stat_entry, h.hash_entry
      FROM (SELECT h.client_id, h.path_type, h.path_id,
                   MAX(h.timestamp) AS timestamp
              FROM client_path_hash_entries AS h
        INNER JOIN hash_blob_references AS b
                ON b.hash_id = h.sha256
             WHERE {conditions}
          GROUP BY client_id, path_type, path_id) AS t
 LEFT JOIN client_path_stat_entries AS s
        ON s.client_id = t.client_id
       AND s.path_type = t.path_type
       AND s.path_id = t.path_id
       AND s.timestamp = t.timestamp
 LEFT JOIN client_path_hash_entries AS h
        ON h.client_id = t.client_id
       AND h.path_type = t.path_type
       AND h.path_id = t.path_id
       AND h.timestamp = t.timestamp
    """

    path_conditions = []

    for client_path in client_paths:
      path_conditions.append("""
      (client_id = %s AND path_type = %s AND path_id = %s)
      """)
      params.append(db_utils.ClientIDToInt(client_path.client_id))
      params.append(int(client_path.path_type))
      params.append(client_path.path_id.AsBytes())

    conditions = " OR ".join(path_conditions)
    if max_timestamp is not None:
      conditions = "({}) AND UNIX_TIMESTAMP(timestamp) <= %s".format(conditions)
      params.append(mysql_utils.RDFDatetimeToTimestamp(max_timestamp))

    cursor.execute(query.format(conditions=conditions), params)
    for row in cursor.fetchall():
      # fmt: off
      (client_id, path_type, path_id_bytes, timestamp,
       stat_entry_bytes, hash_entry_bytes) = row
      # fmt: on

      path_id = rdf_objects.PathID.FromSerializedBytes(path_id_bytes)
      components = path_id_components[path_id]

      client_path = db.ClientPath(
          client_id=db_utils.IntToClientID(client_id),
          path_type=path_type,
          components=path_id_components[path_id],
      )

      path_info = objects_pb2.PathInfo(
          path_type=objects_pb2.PathInfo.PathType.Name(path_type),
          components=components,
      )

      datetime = mysql_utils.TimestampToMicrosecondsSinceEpoch
      if timestamp is not None:
        path_info.timestamp = datetime(timestamp)

      if stat_entry_bytes is not None:
        path_info.stat_entry.ParseFromString(stat_entry_bytes)
      if hash_entry_bytes is not None:
        path_info.hash_entry.ParseFromString(hash_entry_bytes)

      path_infos[client_path] = path_info

    return path_infos
