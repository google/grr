#!/usr/bin/env python
"""Classes for exporting data from AFF4 to the rest of the world.

Exporters defined here convert various complex RDFValues to simple RDFValues
(without repeated fields, without recursive field definitions) that can
easily be written to a relational database or just to a set of files.
"""

from typing import Iterable

from grr_response_proto import export_pb2
from grr_response_proto import osquery_pb2
from grr_response_server.export_converters import base


class OsqueryTableExportConverterProto(
    base.ExportConverterProto[osquery_pb2.OsqueryTable]
):
  """An export converter for transforming osquery table protos."""

  input_proto_type = osquery_pb2.OsqueryTable
  output_proto_types = (export_pb2.ExportedOsqueryValue,)

  def Convert(
      self,
      metadata: export_pb2.ExportedMetadata,
      table: osquery_pb2.OsqueryTable,
  ) -> Iterable[export_pb2.ExportedOsqueryValue]:

    column_names = [col.name for col in table.header.columns]

    for row_number, row in enumerate(table.rows):
      for value_index, value in enumerate(row.values):
        yield export_pb2.ExportedOsqueryValue(
            metadata=metadata,
            query=table.query,
            row_number=row_number,
            column_name=column_names[value_index],
            value=value,
        )


class OsqueryResultExportConverterProto(
    base.ExportConverterProto[osquery_pb2.OsqueryResult]
):
  """An export converter for transforming osquery table protos."""

  input_proto_type = osquery_pb2.OsqueryResult
  output_proto_types = (export_pb2.ExportedOsqueryValue,)

  def Convert(
      self,
      metadata: export_pb2.ExportedMetadata,
      result: osquery_pb2.OsqueryResult,
  ) -> Iterable[export_pb2.ExportedOsqueryValue]:

    table_converter = OsqueryTableExportConverterProto()
    yield from table_converter.Convert(metadata, result.table)
