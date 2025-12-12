#!/usr/bin/env python
"""Plugin that exports results as SQLite db scripts."""

import io
import os
import sqlite3
from typing import Any, Callable, Iterator
import zipfile

import yaml

from google.protobuf import descriptor
from google.protobuf import message
from grr_response_core.lib import utils
from grr_response_core.lib.util import collection
from grr_response_server import instant_output_plugin


class Converter:
  """Holds information for converting proto fields to SQLite types.

  Attributes:
    sqlite_type: The SQLite type name (e.g., "REAL", "INTEGER", "TEXT").
    convert_fn: A callable to convert the Python value to a type suitable for
      the SQLite column.
  """

  def __init__(
      self,
      sqlite_type: str,
      convert_fn: Callable[[Any], Any],
  ):
    """Initializes the Converter.

    Args:
      sqlite_type: The SQLite type name (e.g., "REAL", "INTEGER", "TEXT").
      convert_fn: A callable to convert the Python value to a type suitable for
        the SQLite column.
    """
    self.sqlite_type = sqlite_type
    self.convert_fn = convert_fn


PROTO_SQLITE_CONVERTERS = {
    descriptor.FieldDescriptor.TYPE_DOUBLE: Converter("REAL", float),
    descriptor.FieldDescriptor.TYPE_FLOAT: Converter("REAL", float),
    descriptor.FieldDescriptor.TYPE_INT64: Converter("INTEGER", int),
    descriptor.FieldDescriptor.TYPE_UINT64: Converter("INTEGER", int),
    descriptor.FieldDescriptor.TYPE_INT32: Converter("INTEGER", int),
    descriptor.FieldDescriptor.TYPE_FIXED64: Converter("INTEGER", int),
    descriptor.FieldDescriptor.TYPE_FIXED32: Converter("INTEGER", int),
    descriptor.FieldDescriptor.TYPE_BOOL: Converter("INTEGER", int),
    descriptor.FieldDescriptor.TYPE_STRING: Converter("TEXT", str),
    descriptor.FieldDescriptor.TYPE_BYTES: Converter("BLOB", bytes),
    descriptor.FieldDescriptor.TYPE_UINT32: Converter("INTEGER", int),
    descriptor.FieldDescriptor.TYPE_ENUM: Converter("TEXT", str),
    descriptor.FieldDescriptor.TYPE_SFIXED32: Converter("INTEGER", int),
    descriptor.FieldDescriptor.TYPE_SFIXED64: Converter("INTEGER", int),
    descriptor.FieldDescriptor.TYPE_SINT32: Converter("INTEGER", int),
    descriptor.FieldDescriptor.TYPE_SINT64: Converter("INTEGER", int),
}


class SqliteInstantOutputPluginProto(
    instant_output_plugin.InstantOutputPluginWithExportConversionProto
):
  """Instant output plugin that converts results into SQLite db commands."""

  plugin_name = "sqlite-zip"
  friendly_name = "SQLite scripts (zipped)"
  description = "Output ZIP archive containing SQLite scripts."
  output_file_extension = ".zip"

  archive_generator: utils.StreamingZipGenerator
  export_counts: dict[str, dict[str, int]]

  ROW_BATCH = 100

  @property
  def path_prefix(self):
    prefix, _ = os.path.splitext(self.output_file_name)
    return prefix

  def Start(self):
    self.archive_generator = utils.StreamingZipGenerator(
        compression=zipfile.ZIP_DEFLATED
    )
    self.export_counts = {}
    return []

  def ProcessUniqueOriginalExportedTypePair(
      self,
      original_rdf_type_name: str,
      exported_values: Iterator[message.Message],
  ) -> Iterator[bytes]:
    first_value = next(exported_values, None)
    if not first_value:
      return

    exported_value_class_name = first_value.__class__.__name__
    yield self.archive_generator.WriteFileHeader(
        "%s/%s_from_%s.sql"
        % (
            self.path_prefix,
            exported_value_class_name,
            original_rdf_type_name,
        )
    )
    table_name = "%s.from_%s" % (
        exported_value_class_name,
        original_rdf_type_name,
    )
    schema = self._GetSqliteSchema(first_value.DESCRIPTOR)

    # We will buffer the sql statements into an in-memory sql database before
    # dumping them to the zip archive. We rely on the PySQLite library for
    # string escaping.
    db_connection = sqlite3.connect(":memory:")
    db_cursor = db_connection.cursor()

    yield self.archive_generator.WriteFileChunk(
        "BEGIN TRANSACTION;\n".encode("utf-8")
    )

    with db_connection:
      buf = io.StringIO()
      buf.write('CREATE TABLE "%s" (\n  ' % table_name)
      column_types = [(k, v.sqlite_type) for k, v in schema.items()]
      buf.write(",\n  ".join(['"%s" %s' % (k, v) for k, v in column_types]))
      buf.write("\n);")
      db_cursor.execute(buf.getvalue())

      chunk = (buf.getvalue() + "\n").encode("utf-8")
      yield self.archive_generator.WriteFileChunk(chunk)

      self._InsertValueIntoDb(table_name, schema, first_value, db_cursor)

    for sql in self._FlushAllRows(db_connection, table_name):
      yield sql
    counter = 1
    for batch in collection.Batch(exported_values, self.ROW_BATCH):
      counter += len(batch)
      with db_connection:
        for value in batch:
          self._InsertValueIntoDb(table_name, schema, value, db_cursor)
      for sql in self._FlushAllRows(db_connection, table_name):
        yield sql

    db_connection.close()
    yield self.archive_generator.WriteFileChunk("COMMIT;\n".encode("utf-8"))
    yield self.archive_generator.WriteFileFooter()

    counts_for_original_type = self.export_counts.setdefault(
        original_rdf_type_name, dict()
    )
    counts_for_original_type[exported_value_class_name] = counter

  def _GetSqliteSchema(self, message_descriptor, prefix=""):
    """Returns a mapping of SQLite column names to Converter objects."""
    schema = dict()
    for (
        field_name,
        field_descriptor,
    ) in message_descriptor.fields_by_name.items():
      if field_descriptor.type == descriptor.FieldDescriptor.TYPE_MESSAGE:
        schema.update(
            self._GetSqliteSchema(
                field_descriptor.message_type,
                prefix="%s%s." % (prefix, field_name),
            )
        )
      else:
        field_name = prefix + field_name
        if field_descriptor.label == descriptor.FieldDescriptor.LABEL_REPEATED:
          schema[field_name] = Converter("TEXT", str)
        else:
          schema[field_name] = PROTO_SQLITE_CONVERTERS[field_descriptor.type]
    return schema

  def _InsertValueIntoDb(self, table_name, schema, value, db_cursor):
    sql_dict = self._ConvertToCanonicalSqlDict(schema, value)
    buf = io.StringIO()
    buf.write('INSERT INTO "%s" (\n  ' % table_name)
    buf.write(",\n  ".join(['"%s"' % k for k in sql_dict.keys()]))
    buf.write("\n)")
    buf.write("VALUES (%s);" % ",".join(["?"] * len(sql_dict)))
    db_cursor.execute(buf.getvalue(), list(sql_dict.values()))

  def _ConvertToCanonicalSqlDict(self, schema, msg, prefix=""):
    """Converts a proto message into a SQL-ready form."""
    flattened_dict = {}
    for (
        field_name,
        field_descriptor,
    ) in msg.DESCRIPTOR.fields_by_name.items():
      if field_descriptor.type == descriptor.FieldDescriptor.TYPE_MESSAGE:
        flattened_dict.update(
            self._ConvertToCanonicalSqlDict(
                schema,
                getattr(msg, field_name),
                prefix="%s%s." % (prefix, field_name),
            )
        )
      else:
        key = prefix + field_name
        converter = schema[key]

        val = getattr(msg, field_name)
        if field_descriptor.label == descriptor.FieldDescriptor.LABEL_REPEATED:
          val = list(val)
        elif field_descriptor.type == descriptor.FieldDescriptor.TYPE_ENUM:
          val = field_descriptor.enum_type.values_by_number[val].name

        flattened_dict[key] = converter.convert_fn(val)
    return flattened_dict

  def _FlushAllRows(self, db_connection, table_name):
    """Copies rows from the given db into the output file then deletes them."""
    for sql in db_connection.iterdump():
      if (
          sql.startswith("CREATE TABLE")
          or sql.startswith("BEGIN TRANSACTION")
          or sql.startswith("COMMIT")
      ):
        # These statements only need to be written once.
        continue
      # The archive generator expects strings (not Unicode objects returned by
      # the pysqlite library).
      yield self.archive_generator.WriteFileChunk((sql + "\n").encode("utf-8"))
    with db_connection:
      db_connection.cursor().execute('DELETE FROM "%s";' % table_name)

  def Finish(self):
    manifest = {"export_stats": self.export_counts}
    manifest_bytes = yaml.safe_dump(manifest).encode("utf-8")

    header = self.path_prefix + "/MANIFEST"
    yield self.archive_generator.WriteFileHeader(header)
    yield self.archive_generator.WriteFileChunk(manifest_bytes)
    yield self.archive_generator.WriteFileFooter()
    yield self.archive_generator.Close()
