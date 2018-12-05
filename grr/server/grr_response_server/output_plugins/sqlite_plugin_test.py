#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Tests for the SQLite instant output plugin."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import datetime
import os
import zipfile


from builtins import range  # pylint: disable=redefined-builtin
from future.utils import iteritems
from future.utils import iterkeys
import sqlite3
import yaml

from grr_response_core.lib import flags
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import type_info
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_server import export
from grr_response_server.output_plugins import sqlite_plugin
from grr_response_server.output_plugins import test_plugins
from grr.test_lib import test_lib


class TestEmbeddedStruct(rdf_structs.RDFProtoStruct):
  """Custom struct for testing schema generation."""

  type_description = type_info.TypeDescriptorSet(
      rdf_structs.ProtoString(name="e_string_field", field_number=1),
      rdf_structs.ProtoDouble(name="e_double_field", field_number=2))


class SqliteTestStruct(rdf_structs.RDFProtoStruct):
  """Custom struct for testing schema generation."""

  type_description = type_info.TypeDescriptorSet(
      rdf_structs.ProtoString(name="string_field", field_number=1),
      rdf_structs.ProtoBinary(name="bytes_field", field_number=2),
      rdf_structs.ProtoUnsignedInteger(name="uint_field", field_number=3),
      rdf_structs.ProtoSignedInteger(name="int_field", field_number=4),
      rdf_structs.ProtoFloat(name="float_field", field_number=5),
      rdf_structs.ProtoDouble(name="double_field", field_number=6),
      rdf_structs.ProtoEnum(
          name="enum_field",
          field_number=7,
          enum_name="EnumField",
          enum={
              "FIRST": 1,
              "SECOND": 2
          }), rdf_structs.ProtoBoolean(name="bool_field", field_number=8),
      rdf_structs.ProtoRDFValue(
          name="urn_field", field_number=9, rdf_type="RDFURN"),
      rdf_structs.ProtoRDFValue(
          name="time_field", field_number=10, rdf_type="RDFDatetime"),
      rdf_structs.ProtoRDFValue(
          name="time_field_seconds",
          field_number=11,
          rdf_type="RDFDatetimeSeconds"),
      rdf_structs.ProtoRDFValue(
          name="duration_field", field_number=12, rdf_type="Duration"),
      rdf_structs.ProtoEmbedded(
          name="embedded_field", field_number=13, nested=TestEmbeddedStruct))


class SqliteInstantOutputPluginTest(test_plugins.InstantOutputPluginTestBase):
  """Tests the SQLite instant output plugin."""

  plugin_cls = sqlite_plugin.SqliteInstantOutputPlugin

  STAT_ENTRY_RESPONSES = [
      rdf_client_fs.StatEntry(
          pathspec=rdf_paths.PathSpec(path="/foo/bar/%d" % i, pathtype="OS"),
          st_mode=33184,  # octal = 100640 => u=rw,g=r,o= => -rw-r-----
          st_ino=1063090,
          st_dev=64512,
          st_nlink=1 + i,
          st_uid=139592,
          st_gid=5000,
          st_size=0,
          st_atime=1493596800,  # Midnight, 01.05.2017 UTC in seconds
          st_mtime=1493683200,  # Midnight, 01.05.2017 UTC in seconds
          st_ctime=1493683200) for i in range(10)
  ]

  def setUp(self):
    super(SqliteInstantOutputPluginTest, self).setUp()
    # We use an in-memory db for testing generated SQL scripts.
    self.db_connection = sqlite3.connect(":memory:")
    self.db_cursor = self.db_connection.cursor()

  def tearDown(self):
    super(SqliteInstantOutputPluginTest, self).tearDown()
    self.db_connection.close()

  def ProcessValuesToZip(self, values_by_cls):
    fd_path = self.ProcessValues(values_by_cls)
    file_basename, _ = os.path.splitext(os.path.basename(fd_path))
    return zipfile.ZipFile(fd_path), file_basename

  def testColumnTypeInference(self):
    schema = self.plugin._GetSqliteSchema(SqliteTestStruct)
    column_types = {k: v.sqlite_type for k, v in iteritems(schema)}
    self.assertEqual(
        column_types, {
            "string_field": "TEXT",
            "bytes_field": "TEXT",
            "uint_field": "INTEGER",
            "int_field": "INTEGER",
            "float_field": "REAL",
            "double_field": "REAL",
            "enum_field": "TEXT",
            "bool_field": "INTEGER",
            "urn_field": "TEXT",
            "time_field": "INTEGER",
            "time_field_seconds": "INTEGER",
            "duration_field": "INTEGER",
            "embedded_field.e_string_field": "TEXT",
            "embedded_field.e_double_field": "REAL"
        })

  def testConversionToCanonicalSqlDict(self):
    schema = self.plugin._GetSqliteSchema(SqliteTestStruct)
    test_struct = SqliteTestStruct(
        string_field="string_value",
        bytes_field=b"bytes_value",
        uint_field=123,
        int_field=456,
        float_field=0.123,
        double_field=0.456,
        enum_field="SECOND",
        bool_field=True,
        urn_field=rdfvalue.RDFURN("www.test.com"),
        time_field=rdfvalue.RDFDatetime.FromDatetime(
            datetime.datetime(2017, 5, 1)),
        time_field_seconds=rdfvalue.RDFDatetimeSeconds.FromDatetime(
            datetime.datetime(2017, 5, 2)),
        duration_field=rdfvalue.Duration.FromSeconds(123),
        embedded_field=TestEmbeddedStruct(
            e_string_field="e_string_value", e_double_field=0.789))
    sql_dict = self.plugin._ConvertToCanonicalSqlDict(
        schema, test_struct.ToPrimitiveDict())
    self.assertEqual(
        sql_dict,
        {
            "string_field": "string_value",
            "bytes_field": b"bytes_value",
            "uint_field": 123,
            "int_field": 456,
            "float_field": 0.123,
            "double_field": 0.456,
            "enum_field": "SECOND",
            "bool_field": 1,
            "urn_field": "aff4:/www.test.com",
            "time_field": 1493596800000000,  # Midnight 01.05.2017 UTC, micros
            "time_field_seconds": 1493683200000000,  # Midnight, May 2
            "duration_field": 123000000,
            "embedded_field.e_string_field": "e_string_value",
            "embedded_field.e_double_field": 0.789
        })

  def testExportedFilenamesAndManifestForValuesOfSameType(self):
    zip_fd, prefix = self.ProcessValuesToZip(
        {rdf_client_fs.StatEntry: self.STAT_ENTRY_RESPONSES})
    self.assertEqual(
        set(zip_fd.namelist()),
        {"%s/MANIFEST" % prefix,
         "%s/ExportedFile_from_StatEntry.sql" % prefix})
    parsed_manifest = yaml.load(zip_fd.read("%s/MANIFEST" % prefix))
    self.assertEqual(parsed_manifest,
                     {"export_stats": {
                         "StatEntry": {
                             "ExportedFile": 10
                         }
                     }})

  def testExportedTableStructureForValuesOfSameType(self):
    zip_fd, prefix = self.ProcessValuesToZip(
        {rdf_client_fs.StatEntry: self.STAT_ENTRY_RESPONSES})
    sqlite_dump = zip_fd.read("%s/ExportedFile_from_StatEntry.sql" % prefix)
    # Import the sql dump into an in-memory db.
    with self.db_connection:
      self.db_cursor.executescript(sqlite_dump)

    # See what tables were written to the db.
    self.db_cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = self.db_cursor.fetchall()
    self.assertLen(tables, 1)
    self.assertEqual(tables[0][0], "ExportedFile.from_StatEntry")

    # Ensure all columns in the schema exist in the in-memory table.
    self.db_cursor.execute("PRAGMA table_info('ExportedFile.from_StatEntry');")
    columns = {row[1] for row in self.db_cursor.fetchall()}
    schema = self.plugin._GetSqliteSchema(export.ExportedFile)
    column_types = {k: v.sqlite_type for k, v in iteritems(schema)}
    self.assertEqual(columns, set(iterkeys(schema)))
    self.assertEqual(column_types["metadata.client_urn"], "TEXT")
    self.assertEqual(column_types["st_ino"], "INTEGER")
    self.assertEqual(column_types["st_atime"], "INTEGER")

  def testExportedRowsForValuesOfSameType(self):
    zip_fd, prefix = self.ProcessValuesToZip(
        {rdf_client_fs.StatEntry: self.STAT_ENTRY_RESPONSES})
    sqlite_dump = zip_fd.read("%s/ExportedFile_from_StatEntry.sql" % prefix)

    # Import the sql dump into an in-memory db.
    with self.db_connection:
      self.db_cursor.executescript(sqlite_dump)

    select_columns = [
        "metadata.client_urn", "metadata.source_urn", "urn", "st_mode",
        "st_ino", "st_dev", "st_nlink", "st_uid", "st_gid", "st_size",
        "st_atime", "st_mtime", "st_ctime", "st_blksize", "st_rdev", "symlink"
    ]
    escaped_column_names = ["\"%s\"" % c for c in select_columns]
    self.db_cursor.execute(
        "SELECT %s FROM "
        "\"ExportedFile.from_StatEntry\";" % ",".join(escaped_column_names))
    rows = self.db_cursor.fetchall()
    self.assertLen(rows, 10)
    for i, row in enumerate(rows):
      results = {k: row[j] for j, k in enumerate(select_columns)}
      expected_results = {
          "metadata.client_urn": self.client_id,
          "metadata.source_urn": self.results_urn,
          "urn": self.client_id.Add("/fs/os/foo/bar").Add(str(i)),
          "st_mode": "-rw-r-----",
          "st_ino": 1063090,
          "st_dev": 64512,
          "st_nlink": i + 1,
          "st_uid": 139592,
          "st_gid": 5000,
          "st_size": 0,
          "st_atime": 1493596800000000,
          "st_mtime": 1493683200000000,
          "st_ctime": 1493683200000000,
          "st_blksize": 0,
          "st_rdev": 0,
          "symlink": ""
      }
      self.assertEqual(results, expected_results)

  def testExportedFilenamesAndManifestForValuesOfMultipleTypes(self):
    zip_fd, prefix = self.ProcessValuesToZip({
        rdf_client_fs.StatEntry: [
            rdf_client_fs.StatEntry(
                pathspec=rdf_paths.PathSpec(path="/foo/bar", pathtype="OS"))
        ],
        rdf_client.Process: [rdf_client.Process(pid=42)]
    })
    self.assertEqual(
        set(zip_fd.namelist()), {
            "%s/MANIFEST" % prefix,
            "%s/ExportedFile_from_StatEntry.sql" % prefix,
            "%s/ExportedProcess_from_Process.sql" % prefix
        })

    parsed_manifest = yaml.load(zip_fd.read("%s/MANIFEST" % prefix))
    self.assertEqual(
        parsed_manifest, {
            "export_stats": {
                "StatEntry": {
                    "ExportedFile": 1
                },
                "Process": {
                    "ExportedProcess": 1
                }
            }
        })

  def testExportedRowsForValuesOfMultipleTypes(self):
    zip_fd, prefix = self.ProcessValuesToZip({
        rdf_client_fs.StatEntry: [
            rdf_client_fs.StatEntry(
                pathspec=rdf_paths.PathSpec(path="/foo/bar", pathtype="OS"))
        ],
        rdf_client.Process: [rdf_client.Process(pid=42)]
    })
    with self.db_connection:
      stat_entry_script = zip_fd.read(
          "%s/ExportedFile_from_StatEntry.sql" % prefix)
      process_script = zip_fd.read(
          "%s/ExportedProcess_from_Process.sql" % prefix)
      self.db_cursor.executescript(stat_entry_script)
      self.db_cursor.executescript(process_script)

    self.db_cursor.execute(
        "SELECT \"metadata.client_urn\", \"metadata.source_urn\", urn "
        "FROM \"ExportedFile.from_StatEntry\";")
    stat_entry_results = self.db_cursor.fetchall()
    self.assertLen(stat_entry_results, 1)
    # Client URN
    self.assertEqual(stat_entry_results[0][0], str(self.client_id))
    # Source URN
    self.assertEqual(stat_entry_results[0][1], str(self.results_urn))
    # URN
    self.assertEqual(stat_entry_results[0][2],
                     self.client_id.Add("/fs/os/foo/bar"))

    self.db_cursor.execute(
        "SELECT \"metadata.client_urn\", \"metadata.source_urn\", pid "
        "FROM \"ExportedProcess.from_Process\";")
    process_results = self.db_cursor.fetchall()
    self.assertLen(process_results, 1)
    # Client URN
    self.assertEqual(process_results[0][0], str(self.client_id))
    # Source URN
    self.assertEqual(process_results[0][1], str(self.results_urn))
    # PID
    self.assertEqual(process_results[0][2], 42)

  def testHandlingOfNonAsciiCharacters(self):
    zip_fd, prefix = self.ProcessValuesToZip({
        rdf_client_fs.StatEntry: [
            rdf_client_fs.StatEntry(
                pathspec=rdf_paths.PathSpec(path="/中国新闻网新闻中", pathtype="OS"))
        ]
    })
    self.assertEqual(
        set(zip_fd.namelist()),
        {"%s/MANIFEST" % prefix,
         "%s/ExportedFile_from_StatEntry.sql" % prefix})

    with self.db_connection:
      self.db_cursor.executescript(
          zip_fd.read("%s/ExportedFile_from_StatEntry.sql" % prefix))

    self.db_cursor.execute("SELECT urn FROM \"ExportedFile.from_StatEntry\";")
    results = self.db_cursor.fetchall()
    self.assertLen(results, 1)
    self.assertEqual(results[0][0], self.client_id.Add("/fs/os/中国新闻网新闻中"))

  def testHandlingOfMultipleRowBatches(self):
    num_rows = self.__class__.plugin_cls.ROW_BATCH * 2 + 1

    responses = []
    for i in range(num_rows):
      responses.append(
          rdf_client_fs.StatEntry(
              pathspec=rdf_paths.PathSpec(
                  path="/foo/bar/%d" % i, pathtype="OS")))

    zip_fd, prefix = self.ProcessValuesToZip(
        {rdf_client_fs.StatEntry: responses})
    with self.db_connection:
      self.db_cursor.executescript(
          zip_fd.read("%s/ExportedFile_from_StatEntry.sql" % prefix))
    self.db_cursor.execute("SELECT urn FROM \"ExportedFile.from_StatEntry\";")
    results = self.db_cursor.fetchall()
    self.assertLen(results, num_rows)
    for i in range(num_rows):
      self.assertEqual(results[i][0],
                       self.client_id.Add("/fs/os/foo/bar/%d" % i))


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
