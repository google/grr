#!/usr/bin/env python
"""The MySQL database methods for path handling."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from future.utils import iteritems
from future.utils import iterkeys

import MySQLdb

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import crypto as rdf_crypto
from grr_response_server.databases import db
from grr_response_server.databases import db_utils
from grr_response_server.databases import mysql_utils
from grr_response_server.rdfvalues import objects as rdf_objects


class MySQLDBPathMixin(object):
  """MySQLDB mixin for path related functions."""

  @mysql_utils.WithTransaction(readonly=True)
  def ReadPathInfo(self,
                   client_id,
                   path_type,
                   components,
                   timestamp=None,
                   cursor=None):
    """Retrieves a path info record for a given path."""
    if timestamp is None:
      path_infos = self.ReadPathInfos(client_id, path_type, [components])

      path_info = path_infos[components]
      if path_info is None:
        raise db.UnknownPathError(
            client_id=client_id, path_type=path_type, components=components)

      return path_info

    query = """
    SELECT directory, UNIX_TIMESTAMP(p.timestamp),
           stat_entry, UNIX_TIMESTAMP(last_stat_entry_timestamp),
           hash_entry, UNIX_TIMESTAMP(last_hash_entry_timestamp)
      FROM client_paths as p
 LEFT JOIN (SELECT client_id, path_type, path_id, stat_entry
              FROM client_path_stat_entries
             WHERE client_id = %(client_id)s
               AND path_type = %(path_type)s
               AND path_id = %(path_id)s
               AND UNIX_TIMESTAMP(timestamp) <= %(timestamp)s
          ORDER BY timestamp DESC
             LIMIT 1) AS s
        ON p.client_id = s.client_id
       AND p.path_type = s.path_type
       AND p.path_id = s.path_id
 LEFT JOIN (SELECT client_id, path_type, path_id, hash_entry
              FROM client_path_hash_entries
             WHERE client_id = %(client_id)s
               AND path_type = %(path_type)s
               AND path_id = %(path_id)s
               AND UNIX_TIMESTAMP(timestamp) <= %(timestamp)s
          ORDER BY timestamp DESC
             LIMIT 1) AS h
        ON p.client_id = h.client_id
       AND p.path_type = h.path_type
       AND p.path_id = h.path_id
     WHERE p.client_id = %(client_id)s
       AND p.path_type = %(path_type)s
       AND p.path_id = %(path_id)s
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
          client_id=client_id, path_type=path_type, components=components)

    # pyformat: disable
    (directory, timestamp,
     stat_entry_bytes, last_stat_entry_timestamp,
     hash_entry_bytes, last_hash_entry_timestamp) = row
    # pyformat: enable

    if stat_entry_bytes is not None:
      stat_entry = rdf_client_fs.StatEntry.FromSerializedString(
          stat_entry_bytes)
    else:
      stat_entry = None

    if hash_entry_bytes is not None:
      hash_entry = rdf_crypto.Hash.FromSerializedString(hash_entry_bytes)
    else:
      hash_entry = None

    datetime = mysql_utils.TimestampToRDFDatetime
    return rdf_objects.PathInfo(
        path_type=path_type,
        components=components,
        timestamp=datetime(timestamp),
        last_stat_entry_timestamp=datetime(last_stat_entry_timestamp),
        last_hash_entry_timestamp=datetime(last_hash_entry_timestamp),
        directory=directory,
        stat_entry=stat_entry,
        hash_entry=hash_entry)

  @mysql_utils.WithTransaction(readonly=True)
  def ReadPathInfos(self, client_id, path_type, components_list, cursor=None):
    """Retrieves path info records for given paths."""

    if not components_list:
      return {}

    path_ids = list(map(rdf_objects.PathID.FromComponents, components_list))

    path_infos = {components: None for components in components_list}

    query = """
    SELECT path, directory, UNIX_TIMESTAMP(client_paths.timestamp),
           stat_entry, UNIX_TIMESTAMP(last_stat_entry_timestamp),
           hash_entry, UNIX_TIMESTAMP(last_hash_entry_timestamp)
      FROM client_paths
 LEFT JOIN client_path_stat_entries ON
           (client_paths.client_id = client_path_stat_entries.client_id AND
            client_paths.path_type = client_path_stat_entries.path_type AND
            client_paths.path_id = client_path_stat_entries.path_id AND
            client_paths.last_stat_entry_timestamp = client_path_stat_entries.timestamp)
 LEFT JOIN client_path_hash_entries ON
           (client_paths.client_id = client_path_hash_entries.client_id AND
            client_paths.path_type = client_path_hash_entries.path_type AND
            client_paths.path_id = client_path_hash_entries.path_id AND
            client_paths.last_hash_entry_timestamp = client_path_hash_entries.timestamp)
     WHERE client_paths.client_id = %(client_id)s
       AND client_paths.path_type = %(path_type)s
       AND client_paths.path_id IN %(path_ids)s
    """
    values = {
        "client_id": db_utils.ClientIDToInt(client_id),
        "path_type": int(path_type),
        "path_ids": [path_id.AsBytes() for path_id in path_ids]
    }

    cursor.execute(query, values)
    for row in cursor.fetchall():
      # pyformat: disable
      (path, directory, timestamp,
       stat_entry_bytes, last_stat_entry_timestamp,
       hash_entry_bytes, last_hash_entry_timestamp) = row
      # pyformat: enable
      components = mysql_utils.PathToComponents(path)

      if stat_entry_bytes is not None:
        stat_entry = rdf_client_fs.StatEntry.FromSerializedString(
            stat_entry_bytes)
      else:
        stat_entry = None

      if hash_entry_bytes is not None:
        hash_entry = rdf_crypto.Hash.FromSerializedString(hash_entry_bytes)
      else:
        hash_entry = None

      datetime = mysql_utils.TimestampToRDFDatetime
      path_info = rdf_objects.PathInfo(
          path_type=path_type,
          components=components,
          timestamp=datetime(timestamp),
          last_stat_entry_timestamp=datetime(last_stat_entry_timestamp),
          last_hash_entry_timestamp=datetime(last_hash_entry_timestamp),
          directory=directory,
          stat_entry=stat_entry,
          hash_entry=hash_entry)

      path_infos[components] = path_info

    return path_infos

  def WritePathInfos(self, client_id, path_infos):
    """Writes a collection of path_info records for a client."""
    try:
      self._MultiWritePathInfos({client_id: path_infos})
    except MySQLdb.IntegrityError as error:
      raise db.UnknownClientError(client_id=client_id, cause=error)

  def MultiWritePathInfos(self, path_infos):
    """Writes a collection of path info records for specified clients."""
    try:
      self._MultiWritePathInfos(path_infos)
    except MySQLdb.IntegrityError as error:
      client_ids = list(iterkeys(path_infos))
      raise db.AtLeastOneUnknownClientError(client_ids=client_ids, cause=error)

  @mysql_utils.WithTransaction()
  def _MultiWritePathInfos(self, path_infos, cursor=None):
    """Writes a collection of path info records for specified clients."""
    now = rdfvalue.RDFDatetime.Now()

    path_info_values = []
    parent_path_info_values = []

    stat_entry_keys = []
    stat_entry_values = []

    hash_entry_keys = []
    hash_entry_values = []

    for client_id, client_path_infos in iteritems(path_infos):
      for path_info in client_path_infos:
        path = mysql_utils.ComponentsToPath(path_info.components)

        key = (
            db_utils.ClientIDToInt(client_id),
            int(path_info.path_type),
            path_info.GetPathID().AsBytes(),
        )

        path_info_values.append(key + (mysql_utils.RDFDatetimeToTimestamp(now),
                                       path, bool(path_info.directory),
                                       len(path_info.components)))

        if path_info.HasField("stat_entry"):
          stat_entry_keys.extend(key)
          stat_entry_values.append(key +
                                   (mysql_utils.RDFDatetimeToTimestamp(now),
                                    path_info.stat_entry.SerializeToString()))

        if path_info.HasField("hash_entry"):
          hash_entry_keys.extend(key)
          hash_entry_values.append(key +
                                   (mysql_utils.RDFDatetimeToTimestamp(now),
                                    path_info.hash_entry.SerializeToString(),
                                    path_info.hash_entry.sha256.AsBytes()))

        # TODO(hanuszczak): Implement a trie in order to avoid inserting
        # duplicated records.
        for parent_path_info in path_info.GetAncestors():
          path = mysql_utils.ComponentsToPath(parent_path_info.components)
          parent_path_info_values.append((
              db_utils.ClientIDToInt(client_id),
              int(parent_path_info.path_type),
              parent_path_info.GetPathID().AsBytes(),
              path,
              len(parent_path_info.components),
          ))

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
      cursor.executemany(query, path_info_values)

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

      condition = "(client_id = %s AND path_type = %s AND path_id = %s)"

      query = """
        UPDATE client_paths
        SET last_stat_entry_timestamp = FROM_UNIXTIME(%s)
        WHERE {}
      """.format(" OR ".join([condition] * len(stat_entry_values)))

      params = [mysql_utils.RDFDatetimeToTimestamp(now)] + stat_entry_keys
      cursor.execute(query, params)

    if hash_entry_values:
      query = """
        INSERT INTO client_path_hash_entries(client_id, path_type, path_id,
                                             timestamp,
                                             hash_entry, sha256)
        VALUES (%s, %s, %s, FROM_UNIXTIME(%s), %s, %s)
      """
      cursor.executemany(query, hash_entry_values)

      condition = "(client_id = %s AND path_type = %s AND path_id = %s)"

      query = """
        UPDATE client_paths
        SET last_hash_entry_timestamp = FROM_UNIXTIME(%s)
        WHERE {}
      """.format(" OR ".join([condition] * len(hash_entry_values)))

      params = [mysql_utils.RDFDatetimeToTimestamp(now)] + hash_entry_keys
      cursor.execute(query, params)

  @mysql_utils.WithTransaction(readonly=True)
  def ListDescendentPathInfos(self,
                              client_id,
                              path_type,
                              components,
                              timestamp=None,
                              max_depth=None,
                              cursor=None):
    """Lists path info records that correspond to descendants of given path."""
    path_infos = []

    query = ""

    path = mysql_utils.ComponentsToPath(components)
    values = {
        "client_id": db_utils.ClientIDToInt(client_id),
        "path_type": int(path_type),
        "path": db_utils.EscapeWildcards(path),
    }

    query += """
    SELECT path, directory, UNIX_TIMESTAMP(p.timestamp),
           stat_entry, UNIX_TIMESTAMP(last_stat_entry_timestamp),
           hash_entry, UNIX_TIMESTAMP(last_hash_entry_timestamp)
      FROM client_paths AS p
    """
    if timestamp is None:
      query += """
      LEFT JOIN client_path_stat_entries AS s ON
                (p.client_id = s.client_id AND
                 p.path_type = s.path_type AND
                 p.path_id = s.path_id AND
                 p.last_stat_entry_timestamp = s.timestamp)
      LEFT JOIN client_path_hash_entries AS h ON
                (p.client_id = h.client_id AND
                 p.path_type = h.path_type AND
                 p.path_id = h.path_id AND
                 p.last_hash_entry_timestamp = h.timestamp)
      """
      only_explicit = False
    else:
      query += """
      LEFT JOIN (SELECT sr.client_id, sr.path_type, sr.path_id, sr.stat_entry
                   FROM client_path_stat_entries AS sr
             INNER JOIN (SELECT client_id, path_type, path_id,
                                MAX(timestamp) AS max_timestamp
                           FROM client_path_stat_entries
                          WHERE UNIX_TIMESTAMP(timestamp) <= %(timestamp)s
                       GROUP BY client_id, path_type, path_id) AS st
                     ON sr.client_id = st.client_id
                    AND sr.path_type = st.path_type
                    AND sr.path_id = st.path_id
                    AND sr.timestamp = st.max_timestamp) AS s
             ON (p.client_id = s.client_id AND
                 p.path_type = s.path_type AND
                 p.path_id = s.path_id)
      LEFT JOIN (SELECT hr.client_id, hr.path_type, hr.path_id, hr.hash_entry
                   FROM client_path_hash_entries AS hr
             INNER JOIN (SELECT client_id, path_type, path_id,
                                MAX(timestamp) AS max_timestamp
                           FROM client_path_hash_entries
                          WHERE UNIX_TIMESTAMP(timestamp) <= %(timestamp)s
                       GROUP BY client_id, path_type, path_id) AS ht
                     ON hr.client_id = ht.client_id
                    AND hr.path_type = ht.path_type
                    AND hr.path_id = ht.path_id
                    AND hr.timestamp = ht.max_timestamp) AS h
             ON (p.client_id = h.client_id AND
                 p.path_type = h.path_type AND
                 p.path_id = h.path_id)
      """
      values["timestamp"] = mysql_utils.RDFDatetimeToTimestamp(timestamp)
      only_explicit = True

    query += """
    WHERE p.client_id = %(client_id)s
      AND p.path_type = %(path_type)s
      AND path LIKE concat(%(path)s, '/%%')
    """

    if max_depth is not None:
      query += """
      AND depth <= %(depth)s
      """
      values["depth"] = len(components) + max_depth

    cursor.execute(query, values)
    for row in cursor.fetchall():
      # pyformat: disable
      (path, directory, timestamp,
       stat_entry_bytes, last_stat_entry_timestamp,
       hash_entry_bytes, last_hash_entry_timestamp) = row
      # pyformat: enable

      components = mysql_utils.PathToComponents(path)

      if stat_entry_bytes is not None:
        stat_entry = rdf_client_fs.StatEntry.FromSerializedString(
            stat_entry_bytes)
      else:
        stat_entry = None

      if hash_entry_bytes is not None:
        hash_entry = rdf_crypto.Hash.FromSerializedString(hash_entry_bytes)
      else:
        hash_entry = None

      datetime = mysql_utils.TimestampToRDFDatetime
      path_info = rdf_objects.PathInfo(
          path_type=path_type,
          components=components,
          timestamp=datetime(timestamp),
          last_stat_entry_timestamp=datetime(last_stat_entry_timestamp),
          last_hash_entry_timestamp=datetime(last_hash_entry_timestamp),
          directory=directory,
          stat_entry=stat_entry,
          hash_entry=hash_entry)

      path_infos.append(path_info)

    path_infos.sort(key=lambda _: tuple(_.components))

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
      components = tuple(path_info.components)

      if (path_info.HasField("stat_entry") or
          path_info.HasField("hash_entry") or
          components in has_explicit_ancestor):
        explicit_path_infos.append(path_info)
        has_explicit_ancestor.add(components[:-1])

    # Since we collected explicit paths in reverse order, we need to reverse it
    # again to conform to the interface.
    return list(reversed(explicit_path_infos))

  @mysql_utils.WithTransaction(readonly=True)
  def ReadPathInfosHistories(self,
                             client_id,
                             path_type,
                             components_list,
                             cursor=None):
    """Reads a collection of hash and stat entries for given paths."""
    # MySQL does not handle well empty `IN` clauses so we guard against that.
    if not components_list:
      return {}

    path_infos = {components: [] for components in components_list}

    path_id_components = {}
    for components in components_list:
      path_id = rdf_objects.PathID.FromComponents(components)
      path_id_components[path_id] = components

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
       AND s.path_id IN %(path_ids)s
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
       AND h.path_id IN %(path_ids)s
    """

    params = {
        "client_id": db_utils.ClientIDToInt(client_id),
        "path_type": int(path_type),
        "path_ids": [path_id.AsBytes() for path_id in path_id_components]
    }

    cursor.execute(query, params)
    for row in cursor.fetchall():
      # pyformat: disable
      (stat_entry_path_id_bytes, stat_entry_bytes, stat_entry_timestamp,
       hash_entry_path_id_bytes, hash_entry_bytes, hash_entry_timestamp) = row
      # pyformat: enable

      path_id_bytes = stat_entry_path_id_bytes or hash_entry_path_id_bytes
      path_id = rdf_objects.PathID.FromBytes(path_id_bytes)
      components = path_id_components[path_id]

      timestamp = stat_entry_timestamp or hash_entry_timestamp

      if stat_entry_bytes is not None:
        stat_entry = rdf_client_fs.StatEntry.FromSerializedString(
            stat_entry_bytes)
      else:
        stat_entry = None

      if hash_entry_bytes is not None:
        hash_entry = rdf_crypto.Hash.FromSerializedString(hash_entry_bytes)
      else:
        hash_entry = None

      path_info = rdf_objects.PathInfo(
          path_type=path_type,
          components=components,
          stat_entry=stat_entry,
          hash_entry=hash_entry,
          timestamp=mysql_utils.TimestampToRDFDatetime(timestamp))

      path_infos[components].append(path_info)

    for components in components_list:
      path_infos[components].sort(key=lambda path_info: path_info.timestamp)

    return path_infos

  @mysql_utils.WithTransaction(readonly=True)
  def ReadLatestPathInfosWithHashBlobReferences(self,
                                                client_paths,
                                                max_timestamp=None,
                                                cursor=None):
    """Returns PathInfos that have corresponding HashBlobReferences."""
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
      # pyformat: disable
      (client_id, path_type, path_id_bytes, timestamp,
       stat_entry_bytes, hash_entry_bytes) = row
      # pyformat: enable

      path_id = rdf_objects.PathID.FromBytes(path_id_bytes)
      components = path_id_components[path_id]

      if stat_entry_bytes is not None:
        stat_entry = rdf_client_fs.StatEntry.FromSerializedString(
            stat_entry_bytes)
      else:
        stat_entry = None

      hash_entry = rdf_crypto.Hash.FromSerializedString(hash_entry_bytes)

      client_path = db.ClientPath(
          client_id=db_utils.IntToClientID(client_id),
          path_type=path_type,
          components=path_id_components[path_id])

      path_info = rdf_objects.PathInfo(
          path_type=path_type,
          components=components,
          stat_entry=stat_entry,
          hash_entry=hash_entry,
          timestamp=mysql_utils.TimestampToRDFDatetime(timestamp))

      path_infos[client_path] = path_info

    return path_infos
