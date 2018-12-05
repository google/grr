#!/usr/bin/env python
"""Plugin that exports results as SQLite db scripts."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import collections
import io
import os
import zipfile


from future.utils import iteritems
from future.utils import iterkeys
from future.utils import itervalues
import sqlite3
import yaml

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.lib.util import collection
from grr_response_server import instant_output_plugin


class Rdf2SqliteAdapter(object):
  """An adapter for converting RDF values to a SQLite-friendly form."""

  class Converter(object):

    def __init__(self, sqlite_type, convert_fn):
      self.sqlite_type = sqlite_type
      self.convert_fn = convert_fn

  # PySQLite prefers dealing with unicode objects.
  DEFAULT_CONVERTER = Converter("TEXT", utils.SmartUnicode)

  INT_CONVERTER = Converter("INTEGER", int)

  # Converters for fields that have a semantic type annotation in their
  # protobuf definition.
  SEMANTIC_CONVERTERS = {
      rdfvalue.RDFInteger:
          INT_CONVERTER,
      rdfvalue.RDFBool:
          INT_CONVERTER,  # Sqlite does not have a bool type.
      rdfvalue.RDFDatetime:
          Converter("INTEGER", lambda x: x.AsMicrosecondsSinceEpoch()),
      rdfvalue.RDFDatetimeSeconds:
          Converter("INTEGER", lambda x: x.AsSecondsSinceEpoch() * 1000000),
      rdfvalue.Duration:
          Converter("INTEGER", lambda x: x.microseconds),
  }

  # Converters for fields that do not have a semantic type annotation in their
  # protobuf definition.
  NON_SEMANTIC_CONVERTERS = {
      rdf_structs.ProtoUnsignedInteger: INT_CONVERTER,
      rdf_structs.ProtoSignedInteger: INT_CONVERTER,
      rdf_structs.ProtoFixed32: INT_CONVERTER,
      rdf_structs.ProtoFixed64: INT_CONVERTER,
      rdf_structs.ProtoFloat: Converter("REAL", float),
      rdf_structs.ProtoDouble: Converter("REAL", float),
      rdf_structs.ProtoBoolean: INT_CONVERTER,
  }

  @staticmethod
  def GetConverter(type_info):
    if type_info.__class__ is rdf_structs.ProtoRDFValue:
      return Rdf2SqliteAdapter.SEMANTIC_CONVERTERS.get(
          type_info.type, Rdf2SqliteAdapter.DEFAULT_CONVERTER)
    else:
      return Rdf2SqliteAdapter.NON_SEMANTIC_CONVERTERS.get(
          type_info.__class__, Rdf2SqliteAdapter.DEFAULT_CONVERTER)


class SqliteInstantOutputPlugin(
    instant_output_plugin.InstantOutputPluginWithExportConversion):
  """Instant output plugin that converts results into SQLite db commands."""

  plugin_name = "sqlite-zip"
  friendly_name = "SQLite scripts (zipped)"
  description = "Output ZIP archive containing SQLite scripts."
  output_file_extension = ".zip"

  ROW_BATCH = 100

  def __init__(self, *args, **kwargs):
    super(SqliteInstantOutputPlugin, self).__init__(*args, **kwargs)
    self.archive_generator = None  # Created in Start()
    self.export_counts = {}

  @property
  def path_prefix(self):
    prefix, _ = os.path.splitext(self.output_file_name)
    return prefix

  def Start(self):
    self.archive_generator = utils.StreamingZipGenerator(
        compression=zipfile.ZIP_DEFLATED)
    self.export_counts = {}
    return []

  def ProcessSingleTypeExportedValues(self, original_value_type,
                                      exported_values):
    first_value = next(exported_values, None)
    if not first_value:
      return

    if not isinstance(first_value, rdf_structs.RDFProtoStruct):
      raise ValueError("The SQLite plugin only supports export-protos")
    yield self.archive_generator.WriteFileHeader(
        "%s/%s_from_%s.sql" % (self.path_prefix, first_value.__class__.__name__,
                               original_value_type.__name__))
    table_name = "%s.from_%s" % (first_value.__class__.__name__,
                                 original_value_type.__name__)
    schema = self._GetSqliteSchema(first_value.__class__)

    # We will buffer the sql statements into an in-memory sql database before
    # dumping them to the zip archive. We rely on the PySQLite library for
    # string escaping.
    db_connection = sqlite3.connect(":memory:")
    db_cursor = db_connection.cursor()

    yield self.archive_generator.WriteFileChunk("BEGIN TRANSACTION;\n")
    with db_connection:
      buf = io.StringIO()
      buf.write(u"CREATE TABLE \"%s\" (\n  " % table_name)
      column_types = [(k, v.sqlite_type) for k, v in iteritems(schema)]
      buf.write(u",\n  ".join([u"\"%s\" %s" % (k, v) for k, v in column_types]))
      buf.write(u"\n);")
      db_cursor.execute(buf.getvalue())
      yield self.archive_generator.WriteFileChunk(buf.getvalue() + u"\n")
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
    yield self.archive_generator.WriteFileChunk("COMMIT;\n")
    yield self.archive_generator.WriteFileFooter()

    counts_for_original_type = self.export_counts.setdefault(
        original_value_type.__name__, dict())
    counts_for_original_type[first_value.__class__.__name__] = counter

  def _GetSqliteSchema(self, proto_struct_class, prefix=""):
    """Returns a mapping of SQLite column names to Converter objects."""
    schema = collections.OrderedDict()
    for type_info in proto_struct_class.type_infos:
      if type_info.__class__ is rdf_structs.ProtoEmbedded:
        schema.update(
            self._GetSqliteSchema(
                type_info.type, prefix="%s%s." % (prefix, type_info.name)))
      else:
        field_name = utils.SmartStr(prefix + type_info.name)
        schema[field_name] = Rdf2SqliteAdapter.GetConverter(type_info)
    return schema

  def _InsertValueIntoDb(self, table_name, schema, value, db_cursor):
    sql_dict = self._ConvertToCanonicalSqlDict(schema, value.ToPrimitiveDict())
    buf = io.StringIO()
    buf.write(u"INSERT INTO \"%s\" (\n  " % table_name)
    buf.write(u",\n  ".join(["\"%s\"" % k for k in iterkeys(sql_dict)]))
    buf.write(u"\n)")
    buf.write(u"VALUES (%s);" % u",".join([u"?"] * len(sql_dict)))
    db_cursor.execute(buf.getvalue(), list(itervalues(sql_dict)))

  def _ConvertToCanonicalSqlDict(self, schema, raw_dict, prefix=""):
    """Converts a dict of RDF values into a SQL-ready form."""
    flattened_dict = {}
    for k, v in iteritems(raw_dict):
      if isinstance(v, dict):
        flattened_dict.update(
            self._ConvertToCanonicalSqlDict(
                schema, v, prefix="%s%s." % (prefix, k)))
      else:
        field_name = prefix + k
        flattened_dict[field_name] = schema[field_name].convert_fn(v)
    return flattened_dict

  def _FlushAllRows(self, db_connection, table_name):
    """Copies rows from the given db into the output file then deletes them."""
    for sql in db_connection.iterdump():
      if (sql.startswith("CREATE TABLE") or
          sql.startswith("BEGIN TRANSACTION") or sql.startswith("COMMIT")):
        # These statements only need to be written once.
        continue
      # The archive generator expects strings (not Unicode objects returned by
      # the pysqlite library).
      yield self.archive_generator.WriteFileChunk((sql + "\n").encode("utf-8"))
    with db_connection:
      db_connection.cursor().execute("DELETE FROM \"%s\";" % table_name)

  def Finish(self):
    manifest = {"export_stats": self.export_counts}

    header = self.path_prefix + "/MANIFEST"
    yield self.archive_generator.WriteFileHeader(header.encode("utf-8"))
    yield self.archive_generator.WriteFileChunk(yaml.safe_dump(manifest))
    yield self.archive_generator.WriteFileFooter()
    yield self.archive_generator.Close()
