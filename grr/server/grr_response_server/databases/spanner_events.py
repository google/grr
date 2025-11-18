#!/usr/bin/env python
"""A library with audit events methods of Spanner database implementation."""

from typing import Dict, List, Optional, Tuple

from google.cloud import spanner as spanner_lib

from grr_response_core.lib import rdfvalue
from grr_response_proto import objects_pb2
from grr_response_server.databases import db_utils
from grr_response_server.databases import spanner_utils


class EventsMixin:
  """A Spanner database mixin with implementation of audit events methods."""

  db: spanner_utils.Database

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadAPIAuditEntries(
      self,
      username: Optional[str] = None,
      router_method_names: Optional[List[str]] = None,
      min_timestamp: Optional[rdfvalue.RDFDatetime] = None,
      max_timestamp: Optional[rdfvalue.RDFDatetime] = None,
  ) -> List[objects_pb2.APIAuditEntry]:
    """Returns audit entries stored in the database."""
    query = """
    SELECT
      a.Username,
      a.CreationTime,
      a.HttpRequestPath,
      a.RouterMethodName,
      a.ResponseCode
    FROM ApiAuditEntry AS a
    """

    params = {}
    conditions = []

    if username is not None:
      conditions.append("a.Username = {username}")
      params["username"] = username

    if router_method_names:
      param_placeholders = ", ".join([f"{{rmn{i}}}" for i in range(len(router_method_names))])
      for i, rmn in enumerate(router_method_names):
        param_name = f"rmn{i}"
        params[param_name] = rmn
      conditions.append(f"""a.RouterMethodName IN ({param_placeholders})""")

    if min_timestamp is not None:
      conditions.append("a.CreationTime >= {min_timestamp}")
      params["min_timestamp"] = min_timestamp.AsDatetime()

    if max_timestamp is not None:
      conditions.append("a.CreationTime <= {max_timestamp}")
      params["max_timestamp"] = max_timestamp.AsDatetime()

    if conditions:
      query += " WHERE " + " AND ".join(conditions)

    result = []
    for (
        username,
        ts,
        http_request_path,
        router_method_name,
        response_code,
    ) in self.db.ParamQuery(query, params, txn_tag="ReadAPIAuditEntries"):
      result.append(
          objects_pb2.APIAuditEntry(
              username=username,
              timestamp=rdfvalue.RDFDatetime.FromDatetime(
                  ts
              ).AsMicrosecondsSinceEpoch(),
              http_request_path=http_request_path,
              router_method_name=router_method_name,
              response_code=response_code,
          )
      )

    return result

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def CountAPIAuditEntriesByUserAndDay(
      self,
      min_timestamp: Optional[rdfvalue.RDFDatetime] = None,
      max_timestamp: Optional[rdfvalue.RDFDatetime] = None,
  ) -> Dict[Tuple[str, rdfvalue.RDFDatetime], int]:
    """Returns audit entry counts grouped by user and calendar day."""
    query = """
    SELECT
      a.Username,
      TIMESTAMP_TRUNC(a.CreationTime, DAY, "UTC") AS day,
      COUNT(*)
    FROM ApiAuditEntry AS a
    """

    params = {}
    conditions = []

    if min_timestamp is not None:
      conditions.append("a.CreationTime >= {min_timestamp}")
      params["min_timestamp"] = min_timestamp.AsDatetime()

    if max_timestamp is not None:
      conditions.append("a.CreationTime <= {max_timestamp}")
      params["max_timestamp"] = max_timestamp.AsDatetime()

    if conditions:
      query += " WHERE " + " AND ".join(conditions)

    query += " GROUP BY a.Username, day"

    result = {}
    for username, day, count in self.db.ParamQuery(
        query, params, txn_tag="CountAPIAuditEntriesByUserAndDay"
    ):
      result[(username, rdfvalue.RDFDatetime.FromDatetime(day))] = count

    return result

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def WriteAPIAuditEntry(self, entry: objects_pb2.APIAuditEntry):
    """Writes an audit entry to the database."""
    row = {
        "HttpRequestPath": entry.http_request_path,
        "RouterMethodName": entry.router_method_name,
        "Username": entry.username,
        "ResponseCode": entry.response_code,
    }

    if not entry.HasField("timestamp"):
      row["CreationTime"] = spanner_lib.COMMIT_TIMESTAMP
    else:
      row["CreationTime"] = rdfvalue.RDFDatetime.FromMicrosecondsSinceEpoch(
          entry.timestamp
      ).AsDatetime()

    self.db.InsertOrUpdate(
        table="ApiAuditEntry", row=row, txn_tag="WriteAPIAuditEntry"
    )
