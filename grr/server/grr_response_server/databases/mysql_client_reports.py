#!/usr/bin/env python
"""MySQL implementation of DB methods for handling client-report data."""
from __future__ import absolute_import
from __future__ import division

from __future__ import unicode_literals

from typing import cast, Dict, Optional, Text

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import time_utils
from grr_response_core.lib.rdfvalues import stats as rdf_stats
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_server.databases import mysql_utils


class MySQLDBClientReportsMixin(object):
  """Mixin providing an F1 implementation of client-reports DB logic."""

  @mysql_utils.WithTransaction()
  def WriteClientGraphSeries(
      self,
      graph_series,
      client_label,
      timestamp,
      cursor=None,
  ):
    """Writes the provided graphs to the DB with the given client label."""
    args = {
        "client_label": client_label,
        "report_type": graph_series.report_type.SerializeToDataStore(),
        "timestamp": mysql_utils.RDFDatetimeToTimestamp(timestamp),
        "graph_series": graph_series.SerializeToString(),
    }

    query = """
      INSERT INTO client_report_graphs (client_label, report_type, timestamp,
                                        graph_series)
      VALUES (%(client_label)s, %(report_type)s, FROM_UNIXTIME(%(timestamp)s),
              %(graph_series)s)
      ON DUPLICATE KEY UPDATE graph_series = VALUES(graph_series)
    """

    cursor.execute(query, args)

  @mysql_utils.WithTransaction(readonly=True)
  def ReadAllClientGraphSeries(
      self,
      client_label,
      report_type,
      time_range = None,
      cursor=None):
    """Reads graph series for the given label and report-type from the DB."""
    query = """
      SELECT UNIX_TIMESTAMP(timestamp), graph_series
      FROM client_report_graphs
      WHERE client_label = %s AND report_type = %s
    """
    args = [client_label, report_type.SerializeToDataStore()]

    if time_range is not None:
      query += "AND `timestamp` BETWEEN FROM_UNIXTIME(%s) AND FROM_UNIXTIME(%s)"
      args += [
          mysql_utils.RDFDatetimeToTimestamp(time_range.start),
          mysql_utils.RDFDatetimeToTimestamp(time_range.end)
      ]

    cursor.execute(query, args)
    results = {}
    for timestamp, raw_series in cursor.fetchall():
      # TODO(hanuszczak): pytype does not seem to understand overloads, so it is
      # not possible to correctly annotate `TimestampToRDFDatetime`.
      timestamp = cast(rdfvalue.RDFDatetime,
                       mysql_utils.TimestampToRDFDatetime(timestamp))

      series = rdf_stats.ClientGraphSeries.FromSerializedString(raw_series)
      results[timestamp] = series
    return results

  @mysql_utils.WithTransaction(readonly=True)
  def ReadMostRecentClientGraphSeries(
      self,
      client_label,
      report_type,
      cursor=None):
    """Fetches the latest graph series for a client-label from the DB."""
    query = """
      SELECT graph_series
      FROM client_report_graphs
      WHERE client_label = %s AND report_type = %s
      ORDER BY timestamp DESC
      LIMIT 1
    """
    args = [client_label, report_type.SerializeToDataStore()]
    cursor.execute(query, args)
    result = cursor.fetchone()
    if result is None:
      return None
    else:
      return rdf_stats.ClientGraphSeries.FromSerializedString(result[0])
