#!/usr/bin/env python
"""Classes for exporting data from AFF4 to the rest of the world.

Exporters defined here convert various complex RDFValues to simple RDFValues
(without repeated fields, without recursive field definitions) that can
easily be written to a relational database or just to a set of files.
"""

from typing import Any, Iterable

from grr_response_core.lib.rdfvalues import osquery as rdf_osquery
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.lib.util import precondition
from grr_response_proto import export_pb2
from grr_response_proto import osquery_pb2
from grr_response_server.export_converters import base


class OsqueryExportConverter(base.ExportConverter):
  """An export converted class for transforming osquery table values."""

  input_rdf_type = rdf_osquery.OsqueryTable

  _rdf_cls_cache = {}

  @classmethod
  def _RDFClass(cls, table: rdf_osquery.OsqueryTable) -> type[Any]:
    """Creates a dynamic RDF proto struct class for given osquery table.

    The fields of the proto will correspond to the columns of the table.

    Args:
      table: An osquery table for which the class is about to be generated.

    Returns:
      A class object corresponding to the given table.
    """
    rdf_cls_name = "OsqueryTable{}".format(hash(table.query))
    try:
      return cls._rdf_cls_cache[rdf_cls_name]
    except KeyError:
      pass

    rdf_cls = type(rdf_cls_name, (rdf_structs.RDFProtoStruct,), {})
    rdf_cls.AddDescriptor(
        rdf_structs.ProtoEmbedded(
            name="metadata", field_number=1, nested=base.ExportedMetadata
        )
    )

    rdf_cls.AddDescriptor(
        rdf_structs.ProtoString(name="__query__", field_number=2)
    )

    for idx, column in enumerate(table.header.columns):
      # It is possible that RDF column is named "metadata". To avoid name clash
      # we must rename it to `__metadata__`.
      if column.name == "metadata":
        name = "__metadata__"
      else:
        name = column.name

      descriptor = rdf_structs.ProtoString(name=name, field_number=idx + 3)
      rdf_cls.AddDescriptor(descriptor)

    cls._rdf_cls_cache[rdf_cls_name] = rdf_cls
    return rdf_cls

  def Convert(
      self, metadata: base.ExportedMetadata, table: rdf_osquery.OsqueryTable
  ) -> Any:
    precondition.AssertType(table, rdf_osquery.OsqueryTable)

    rdf_cls = self._RDFClass(table)

    for row in table.rows:
      rdf = rdf_cls()
      rdf.metadata = metadata
      rdf.__query__ = table.query.strip()

      for column, value in zip(table.header.columns, row.values):
        # In order to avoid name clash, renaming the column might be required.
        if column.name == "metadata":
          rdf.__metadata__ = value
        else:
          setattr(rdf, column.name, value)

      yield rdf


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
