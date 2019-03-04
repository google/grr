#!/usr/bin/env python
"""A module with RDF values wrapping osquery protobufs."""
from __future__ import absolute_import
from __future__ import division

from __future__ import unicode_literals

from typing import Iterator
from typing import Text

from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import osquery_pb2


class OsqueryArgs(rdf_structs.RDFProtoStruct):
  """An RDF wrapper class for the `OsqueryArgs` proto."""

  protobuf = osquery_pb2.OsqueryArgs
  rdf_deps = []

  def __init__(self, *args, **kwargs):
    super(OsqueryArgs, self).__init__(*args, **kwargs)

    if not self.HasField("timeout_millis"):
      self.timeout_millis = 5 * 60 * 1000  # 5 minutes.


class OsqueryColumn(rdf_structs.RDFProtoStruct):
  """An RDF wrapper class for the `OsqueryColumn` proto."""

  protobuf = osquery_pb2.OsqueryColumn
  rdf_deps = []


class OsqueryHeader(rdf_structs.RDFProtoStruct):
  """An RDF wrapper class for the `OsqueryHeader` proto."""

  protobuf = osquery_pb2.OsqueryHeader
  rdf_deps = [OsqueryColumn]


class OsqueryRow(rdf_structs.RDFProtoStruct):
  """An RDF wrapper class for the `OsqueryRow` proto."""

  protobuf = osquery_pb2.OsqueryRow
  rdf_deps = []


class OsqueryTable(rdf_structs.RDFProtoStruct):
  """An RDF wrapper class for the `OsqueryTable` proto."""

  protobuf = osquery_pb2.OsqueryTable
  rdf_deps = [OsqueryHeader, OsqueryRow]

  def Column(self, column_name):
    """Iterates over values of a given column.

    Args:
      column_name: A nome of the column to retrieve the values for.

    Yields:
      Values of the specified column.

    Raises:
      KeyError: If given column is not present in the table.
    """
    column_idx = None
    for idx, column in enumerate(self.header.columns):
      if column.name == column_name:
        column_idx = idx
        break

    if column_idx is None:
      raise KeyError("Column '{}' not found".format(column_name))

    for row in self.rows:
      yield row.values[column_idx]


class OsqueryResult(rdf_structs.RDFProtoStruct):
  """An RDF wrapper class for the `OsqueryTable` proto."""

  protobuf = osquery_pb2.OsqueryResult
  rdf_deps = [OsqueryTable]
