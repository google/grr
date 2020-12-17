#!/usr/bin/env python
# Lint as: python3
"""A module with RDF values wrapping osquery protobufs."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from typing import Iterator
from typing import Sequence
from typing import Text

from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import osquery_pb2


class OsqueryArgs(rdf_structs.RDFProtoStruct):
  """An RDF wrapper class for the `OsqueryArgs` proto."""

  protobuf = osquery_pb2.OsqueryArgs
  rdf_deps = []


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

  def Column(self, column_name: Text) -> Iterator[Text]:
    """Iterates over values of a given column.

    Args:
      column_name: A name of the column to retrieve the values for.

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

  def Truncated(self, row_count: int) -> "OsqueryTable":
    """Returns a fresh table with the first few rows of the original one.

    Truncated doesn't modify the original table.

    Args:
      row_count: The number of rows to keep in the truncated table

    Returns:
      New OsqueryTable object with maximum row_count rows.
    """
    result = OsqueryTable()

    result.query = self.query
    result.header = self.header
    result.rows = self.rows[:row_count]

    return result


class OsqueryResult(rdf_structs.RDFProtoStruct):
  """An RDF wrapper class for the `OsqueryTable` proto."""

  protobuf = osquery_pb2.OsqueryResult
  rdf_deps = [OsqueryTable]

  def GetTableColumns(self) -> Iterator[str]:
    return (column.name for column in self.table.header.columns)

  def GetTableRows(self) -> Iterator[Sequence[str]]:
    return (row.values for row in self.table.rows)


class OsqueryProgress(rdf_structs.RDFProtoStruct):
  """An RDF wrapper class for the `OsqueryProgress` proto."""

  protobuf = osquery_pb2.OsqueryProgress
  rdf_deps = [OsqueryTable]

