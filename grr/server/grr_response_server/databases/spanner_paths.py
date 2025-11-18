#!/usr/bin/env python
"""A module with path methods of the Spanner database implementation."""
import base64
from typing import Collection, Dict, Iterable, Optional, Sequence

from google.api_core.exceptions import NotFound
from google.cloud import spanner as spanner_lib

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.util import iterator
from grr_response_proto import objects_pb2
from grr_response_server.databases import db as abstract_db
from grr_response_server.databases import db_utils
from grr_response_server.databases import spanner_clients
from grr_response_server.databases import spanner_utils
from grr_response_server.models import paths as models_paths

class PathsMixin:
  """A Spanner database mixin with implementation of path methods."""

  db: spanner_utils.Database

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def WritePathInfos(
      self,
      client_id: str,
      path_infos: Iterable[objects_pb2.PathInfo],
  ) -> None:
    """Writes a collection of path records for a client."""
    # Special case for empty list of paths because Spanner does not like empty
    # mutations. We still have to validate the client id.
    if not path_infos:
      try:
        self.db.Read(table="Clients",
                     key=[client_id],
                     cols=(["ClientId"]),
                     txn_tag="WritePathInfos")
      except NotFound as error:
        raise abstract_db.UnknownClientError(client_id) from error
      return

    def Mutation(mut) -> None:
      ancestors = set()
      file_hash_columns = ["ClientId", "Type", "Path", "CreationTime", "FileHash"]
      file_stat_columns = ["ClientId", "Type", "Path", "CreationTime", "Stat"]
      for path_info in path_infos:
        path_columns = ["ClientId", "Type", "Path", "CreationTime", "IsDir", "Depth"]
        int_path_type = int(path_info.path_type)
        path = EncodePathComponents(path_info.components)

        path_row = [client_id, int_path_type, path,
                    spanner_lib.COMMIT_TIMESTAMP,
                    path_info.directory,
                    len(path_info.components)
        ]

        if path_info.HasField("stat_entry"):
          path_columns.append("LastFileStatTime")
          path_row.append(spanner_lib.COMMIT_TIMESTAMP)

          file_stat_row = [client_id, int_path_type, path,
                           spanner_lib.COMMIT_TIMESTAMP,
                           path_info.stat_entry
          ]
        else:
          file_stat_row = None

        if path_info.HasField("hash_entry"):
          path_columns.append("LastFileHashTime")
          path_row.append(spanner_lib.COMMIT_TIMESTAMP)

          file_hash_row = [client_id, int_path_type, path,
                           spanner_lib.COMMIT_TIMESTAMP,
                          path_info.hash_entry,
          ]
        else:
          file_hash_row = None

        mut.insert_or_update(table="Paths", columns=path_columns, values=[path_row])
        if file_stat_row is not None:
          mut.insert(table="PathFileStats", columns=file_stat_columns, values=[file_stat_row])
        if file_hash_row is not None:
          mut.insert(table="PathFileHashes", columns=file_hash_columns, values=[file_hash_row])

        for path_info_ancestor in models_paths.GetAncestorPathInfos(path_info):
          components = tuple(path_info_ancestor.components)
          ancestors.add((path_info.path_type, components))

      path_columns = ["ClientId", "Type", "Path", "CreationTime", "IsDir", "Depth"]
      for path_type, components in ancestors:
        path_row = [client_id, int(path_type), EncodePathComponents(components),
                    spanner_lib.COMMIT_TIMESTAMP, True, len(components),
        ]
        mut.insert_or_update(table="Paths", columns=path_columns, values=[path_row])

    try:
      self.db.Mutate(Mutation, txn_tag="WritePathInfos")
    except NotFound as error:
      if "Parent row for row [" in str(error):
        raise abstract_db.UnknownClientError(client_id) from error
      else:
        raise

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadPathInfos(
      self,
      client_id: str,
      path_type: objects_pb2.PathInfo.PathType,
      components_list: Collection[Sequence[str]],
  ) -> dict[tuple[str, ...], Optional[objects_pb2.PathInfo]]:
    """Retrieves path info records for given paths."""
    # Early return to avoid issues with unnesting empty path list in the query.
    if not components_list:
      return {}

    results = {tuple(components): None for components in components_list}

    query = """
    SELECT p.Path, p.CreationTime, p.IsDir,
           ps.CreationTime, ps.Stat,
           ph.CreationTime, ph.FileHash
      FROM Paths AS p
           LEFT JOIN PathFileStats AS ps
                  ON p.ClientId = ps.ClientId
                 AND p.Type = ps.Type
                 AND p.Path = ps.Path
                 AND p.LastFileStatTime = ps.CreationTime
           LEFT JOIN PathFileHashes AS ph
                  ON p.ClientId = ph.ClientId
                 AND p.Type = ph.Type
                 AND p.Path = ph.Path
                 AND p.LastFileHashTime = ph.CreationTime
     WHERE p.ClientId = {client_id}
       AND p.Type = {type}
       AND p.Path IN UNNEST({paths})
    """
    params = {
        "client_id": client_id,
        "type": int(path_type),
        "paths": list(map(EncodePathComponents, components_list)),
    }

    for row in self.db.ParamQuery(query, params, txn_tag="ReadPathInfos"):
      path, creation_time, is_dir, *row = row
      stat_creation_time, stat_bytes, *row = row
      hash_creation_time, hash_bytes, *row = row
      () = row

      path_info = objects_pb2.PathInfo(
          path_type=objects_pb2.PathInfo.PathType.Name(int(path_type)),
          components=DecodePathComponents(path),
          timestamp=rdfvalue.RDFDatetime.FromDatetime(
              creation_time
          ).AsMicrosecondsSinceEpoch(),
          directory=is_dir,
      )

      if stat_bytes is not None:
        path_info.stat_entry.ParseFromString(stat_bytes)
        path_info.last_stat_entry_timestamp = rdfvalue.RDFDatetime.FromDatetime(
            stat_creation_time
        ).AsMicrosecondsSinceEpoch()

      if hash_bytes is not None:
        path_info.hash_entry.ParseFromString(hash_bytes)
        path_info.last_hash_entry_timestamp = rdfvalue.RDFDatetime.FromDatetime(
            hash_creation_time
        ).AsMicrosecondsSinceEpoch()

      results[tuple(path_info.components)] = path_info

    return results

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadPathInfo(
      self,
      client_id: str,
      path_type: objects_pb2.PathInfo.PathType,
      components: Sequence[str],
      timestamp: Optional[rdfvalue.RDFDatetime] = None,
  ) -> objects_pb2.PathInfo:
    """Retrieves a path info record for a given path."""
    query = """
    SELECT p.CreationTime,
           p.IsDir,
           -- File stat information.
           p.LastFileStatTime,
           (SELECT s.Stat
              FROM PathFileStats AS s
             WHERE s.ClientId = {client_id}
               AND s.Type = {type}
               AND s.Path = {path}
               AND s.CreationTime <= {timestamp}
             ORDER BY s.CreationTime DESC
             LIMIT 1),
           -- File hash information.
           p.LastFileHashTime,
           (SELECT h.FileHash
              FROM PathFileHashes AS h
             WHERE h.ClientId = {client_id}
               AND h.Type = {type}
               AND h.Path = {path}
               AND h.CreationTime <= {timestamp}
             ORDER BY h.CreationTime DESC
             LIMIT 1)
      FROM Paths AS p
     WHERE p.ClientId = {client_id}
       AND p.Type = {type}
       AND p.Path = {path}
    """
    params = {
        "client_id": client_id,
        "type": int(path_type),
        "path": EncodePathComponents(components),
    }

    if timestamp is not None:
      params["timestamp"] = timestamp.AsDatetime()
    else:
      params["timestamp"] = rdfvalue.RDFDatetime.Now().AsDatetime()

    try:
      row = self.db.ParamQuerySingle(query, params, txn_tag="ReadPathInfo")
    except NotFound:
      raise abstract_db.UnknownPathError(client_id, path_type, components)  # pylint: disable=raise-missing-from

    creation_time, is_dir, *row = row
    last_file_stat_time, stat_bytes, *row = row
    last_file_hash_time, hash_bytes, *row = row
    () = row

    result = objects_pb2.PathInfo(
        path_type=objects_pb2.PathInfo.PathType.Name(int(path_type)),
        components=components,
        directory=is_dir,
        timestamp=rdfvalue.RDFDatetime.FromDatetime(
            creation_time
        ).AsMicrosecondsSinceEpoch(),
    )

    if last_file_stat_time is not None:
      result.last_stat_entry_timestamp = rdfvalue.RDFDatetime.FromDatetime(
          last_file_stat_time
      ).AsMicrosecondsSinceEpoch()
    if last_file_hash_time is not None:
      result.last_hash_entry_timestamp = rdfvalue.RDFDatetime.FromDatetime(
          last_file_hash_time
      ).AsMicrosecondsSinceEpoch()

    if stat_bytes is not None:
      result.stat_entry.ParseFromString(stat_bytes)
    if hash_bytes is not None:
      result.hash_entry.ParseFromString(hash_bytes)

    return result

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ListDescendantPathInfos(
      self,
      client_id: str,
      path_type: objects_pb2.PathInfo.PathType,
      components: Sequence[str],
      timestamp: Optional[rdfvalue.RDFDatetime] = None,
      max_depth: Optional[int] = None,
  ) -> Sequence[objects_pb2.PathInfo]:
    """Lists path info records that correspond to descendants of given path."""
    results = []

    # The query should include not only descendants of the path but the listed
    # path path itself as well. We need to do that to ensure the path actually
    # exists and raise if it does not (or if it is not a directory).
    query = """
    SELECT p.Path,
           p.CreationTime,
           p.IsDir,
           -- File stat information.
           p.LastFileStatTime,
           (SELECT s.Stat
              FROM PathFileStats AS s
             WHERE s.ClientId = p.ClientId
               AND s.Type = p.Type
               AND s.path = p.Path
               AND s.CreationTime <= {timestamp}
             ORDER BY s.CreationTime DESC
             LIMIT 1),
           -- File hash information.
           p.LastFileHashTime,
           (SELECT h.FileHash
              FROM PathFileHashes AS h
             WHERE h.ClientId = p.ClientId
               AND h.Type = p.Type
               AND h.Path = p.Path
               AND h.CreationTime <= {timestamp}
             ORDER BY h.CreationTime DESC
             LIMIT 1)
      FROM Paths AS p
     WHERE p.ClientId = {client_id}
       AND p.Type = {type}
    """
    params = {
        "client_id": client_id,
        "type": int(path_type),
    }

    # We add a constraint on path only if path components are non-empty. Empty
    # path components indicate root path and it means that everything should be
    # listed anyway. Treating the root path the same as other paths leads to
    # issues with trailing slashes.
    if components:
      query += """
      AND (p.Path = {path} OR STARTS_WITH(p.Path, CONCAT({path}, b'/')))
      """
      params["path"] = EncodePathComponents(components)

    if timestamp is not None:
      params["timestamp"] = timestamp.AsDatetime()
    else:
      params["timestamp"] = rdfvalue.RDFDatetime.Now().AsDatetime()

    if max_depth is not None:
      query += " AND p.Depth <= {depth}"
      params["depth"] = len(components) + max_depth

    for row in self.db.ParamQuery(
        query, params, txn_tag="ListDescendantPathInfos"
    ):
      path, creation_time, is_dir, *row = row
      last_file_stat_time, stat_bytes, *row = row
      last_file_hash_time, hash_bytes, *row = row
      () = row

      result = objects_pb2.PathInfo(
          path_type=objects_pb2.PathInfo.PathType.Name(int(path_type)),
          components=DecodePathComponents(path),
          directory=is_dir,
          timestamp=rdfvalue.RDFDatetime.FromDatetime(
              creation_time
          ).AsMicrosecondsSinceEpoch(),
      )

      if last_file_stat_time is not None:
        result.last_stat_entry_timestamp = (
            rdfvalue.RDFDatetime.FromDatetime(last_file_stat_time)
        ).AsMicrosecondsSinceEpoch()
      if last_file_hash_time is not None:
        result.last_hash_entry_timestamp = (
            rdfvalue.RDFDatetime.FromDatetime(last_file_hash_time)
        ).AsMicrosecondsSinceEpoch()

      if stat_bytes is not None:
        result.stat_entry.ParseFromString(stat_bytes)
      if hash_bytes is not None:
        result.hash_entry.ParseFromString(hash_bytes)

      results.append(result)

    results.sort(key=lambda result: tuple(result.components))

    # Special case: we are being asked to list everything under the root path
    # (represented by an empty list of components) but we do not have any path
    # information available. We assume that the root path always exists (even if
    # we did not collect any data yet) so we have to return something but checks
    # that follow would cause us to raise instead.
    if not components and not results:
      return []

    # The first element of the results should be the requested path itself. If
    # it is not, it means that the requested path does not exist and we should
    # raise. We also need to verify that the path is a directory.
    if not results or tuple(results[0].components) != tuple(components):
      raise abstract_db.UnknownPathError(client_id, path_type, components)
    if not results[0].directory:
      raise abstract_db.NotDirectoryPathError(client_id, path_type, components)

    # Once we verified that the path exists and is a directory, we should not
    # include it in the results (since the method is ought to return only real
    # descendants).
    del results[0]

    # If timestamp is not specified we return collected paths as they are. But
    # if the timestamp is given we are only interested in paths that are expli-
    # cit (see below for the definition of "explicitness").
    if timestamp is None:
      return results

    # A path is considered to be explicit if it has an associated stat or hash
    # information or has an ancestor that is explicit. Thus, we traverse results
    # in reverse order so that ancestors are checked for explicitness first.
    explicit_results = list()
    explicit_ancestors = set()

    for result in reversed(results):
      components = tuple(result.components)
      if (
          result.HasField("stat_entry")
          or result.HasField("hash_entry")
          or components in explicit_ancestors
      ):
        explicit_ancestors.add(components[:-1])
        explicit_results.append(result)

    # Since we have been traversing results in the reverse order, explicit re-
    # sults are also reversed. Thus we have to reverse them back.
    return list(reversed(explicit_results))

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadPathInfosHistories(
      self,
      client_id: str,
      path_type: objects_pb2.PathInfo.PathType,
      components_list: Collection[Sequence[str]],
      cutoff: Optional[rdfvalue.RDFDatetime] = None,
  ) -> dict[tuple[str, ...], Sequence[objects_pb2.PathInfo]]:
    """Reads a collection of hash and stat entries for given paths."""
    # Early return in case of empty components list to avoid awkward issues with
    # unnesting an empty array.
    if not components_list:
      return {}

    results = {tuple(components): [] for components in components_list}

    stat_query = """
    SELECT s.Path, s.CreationTime, s.Stat
      FROM PathFileStats AS s
     WHERE s.ClientId = {client_id}
       AND s.Type = {type}
       AND s.Path IN UNNEST({paths})
    """
    hash_query = """
    SELECT h.Path, h.CreationTime, h.FileHash
      FROM PathFileHashes AS h
     WHERE h.ClientId = {client_id}
       AND h.Type = {type}
       AND h.Path IN UNNEST({paths})
    """
    params = {
        "client_id": client_id,
        "type": int(path_type),
        "paths": list(map(EncodePathComponents, components_list)),
    }

    if cutoff is not None:
      stat_query += " AND s.CreationTime <= {cutoff}"
      hash_query += " AND h.CreationTime <= {cutoff}"
      params["cutoff"] = cutoff.AsDatetime()

    query = f"""
      WITH s AS ({stat_query}),
           h AS ({hash_query})
    SELECT s.Path, s.CreationTime, s.Stat,
           h.Path, h.CreationTime, h.FileHash
      FROM s FULL JOIN h ON s.Path = h.Path
    """

    for row in self.db.ParamQuery(
        query, params, txn_tag="ReadPathInfosHistories"
    ):
      stat_path, stat_creation_time, stat_bytes, *row = row
      hash_path, hash_creation_time, hash_bytes, *row = row
      () = row

      # At least one of the two paths is going to be not null. In case both are
      # not null, they are guaranteed to be the same value because of the way
      # full join works.
      components = DecodePathComponents(stat_path or hash_path)

      result = objects_pb2.PathInfo(
          path_type=objects_pb2.PathInfo.PathType.Name(int(path_type)),
          components=components,
      )

      # Either stat or hash or both have to be available, so at least one of the
      # branches below is going to trigger and thus set the timestamp. Not that
      # if both are available, they are guaranteed to have the same timestamp so
      # overriding the value does no harm.
      if stat_bytes is not None:
        result.timestamp = rdfvalue.RDFDatetime.FromDatetime(
            stat_creation_time
        ).AsMicrosecondsSinceEpoch()
        result.stat_entry.ParseFromString(stat_bytes)
      if hash_bytes is not None:
        result.timestamp = rdfvalue.RDFDatetime.FromDatetime(
            hash_creation_time
        ).AsMicrosecondsSinceEpoch()
        result.hash_entry.ParseFromString(hash_bytes)

      results[components].append(result)

    return results

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadLatestPathInfosWithHashBlobReferences(
      self,
      client_paths: Collection[abstract_db.ClientPath],
      max_timestamp: Optional[rdfvalue.RDFDatetime] = None,
  ) -> dict[abstract_db.ClientPath, Optional[objects_pb2.PathInfo]]:
    """Returns path info with corresponding hash blob references."""
    # Early return in case of empty client paths to avoid issues with syntax er-
    # rors due to empty clause list.
    if not client_paths:
      return {}

    params = {}

    key_clauses = []
    for idx, client_path in enumerate(client_paths):
      client_id = client_path.client_id

      key_clauses.append(f"""(
          h.ClientId = {{client_id_{idx}}}
      AND h.Type = {{type_{idx}}}
      AND h.Path = {{path_{idx}}}
      )""")
      params[f"client_id_{idx}"] = client_id
      params[f"type_{idx}"] = int(client_path.path_type)
      params[f"path_{idx}"] = EncodePathComponents(client_path.components)

    if max_timestamp is not None:
      params["cutoff"] = max_timestamp.AsDatetime()
      cutoff_clause = " h.CreationTime <= {cutoff}"
    else:
      cutoff_clause = " TRUE"

    query = f"""
      WITH l AS (SELECT h.ClientId, h.Type, h.Path,
                        MAX(h.CreationTime) AS LastCreationTime
                   FROM PathFileHashes AS h
                        INNER JOIN HashBlobReferences AS b
                                ON h.FileHash.sha256 = b.HashId
                  WHERE ({" OR ".join(key_clauses)})
                    AND {cutoff_clause}
                  GROUP BY h.ClientId, h.Type, h.Path)
    SELECT l.ClientId, l.Type, l.Path, l.LastCreationTime,
           s.Stat, h.FileHash
      FROM l
           LEFT JOIN @{{{{JOIN_METHOD=APPLY_JOIN}}}} PathFileStats AS s
                  ON s.ClientId = l.ClientId
                 AND s.Type = l.Type
                 AND s.Path = l.Path
                 AND s.CreationTime = l.LastCreationTime
           LEFT JOIN @{{{{JOIN_METHOD=APPLY_JOIN}}}} PathFileHashes AS h
                  ON h.ClientId = l.ClientId
                 AND h.Type = l.Type
                 AND h.Path = l.Path
                 AND h.CreationTime = l.LastCreationTime
    """

    results = {client_path: None for client_path in client_paths}

    for row in self.db.ParamQuery(
        query, params, txn_tag="ReadLatestPathInfosWithHashBlobReferences"
    ):
      client_id, int_type, path, creation_time, *row = row
      stat_bytes, hash_bytes = row

      components = DecodePathComponents(path)

      result = objects_pb2.PathInfo(
          path_type=objects_pb2.PathInfo.PathType.Name(int_type),
          components=components,
          timestamp=rdfvalue.RDFDatetime.FromDatetime(
              creation_time
          ).AsMicrosecondsSinceEpoch(),
      )

      if stat_bytes is not None:
        result.stat_entry.ParseFromString(stat_bytes)

      # Hash is guaranteed to be non-null (because of the query construction).
      result.hash_entry.ParseFromString(hash_bytes)

      client_path = abstract_db.ClientPath(
          client_id=client_id,
          path_type=int_type,
          components=components,
      )

      results[client_path] = result

    return results


def EncodePathComponents(components: Sequence[str]) -> bytes:
  """Converts path components into canonical database representation of a path.

  Individual components are required to be non-empty and not contain any slash
  characters ('/').

  Args:
    components: A sequence of path components.

  Returns:
    A canonical database representation of the given path.
  """
  for component in components:
    if not component:
      raise ValueError("Empty path component")
    if _PATH_SEP in component:
      raise ValueError(f"Path component with a '{_PATH_SEP}' character")

  return base64.b64encode(f"{_PATH_SEP}{_PATH_SEP.join(components)}".encode("utf-8"))


def DecodePathComponents(path: bytes) -> tuple[str, ...]:
  """Converts a path in canonical database representation into path components.

  Args:
    path: A path in its canonical database representation.

  Returns:
    A sequence of path components.
  """
  path = base64.b64decode(path).decode("utf-8")

  if not path.startswith(_PATH_SEP):
    raise ValueError(f"Non-absolute path {path!r}")

  if path == _PATH_SEP:
    # A special case for root path, since `str.split` for it gives use two empty
    # strings.
    return ()
  else:
    return tuple(path.split(_PATH_SEP)[1:])


# We use a forward slash as separator as this is the separator accepted by all
# supported platforms (including Windows) and is disallowed to appear in path
# components. Another viable choice would be a null byte character but that is
# very inconvenient to look at when browsing the database.
_PATH_SEP = "/"
