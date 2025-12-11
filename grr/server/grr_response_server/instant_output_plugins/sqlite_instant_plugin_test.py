#!/usr/bin/env python
"""Tests for the SQLite instant output plugin."""

import os
import sqlite3
import zipfile

from absl import app
import yaml

from grr_response_proto import jobs_pb2
from grr_response_proto import sysinfo_pb2
from grr_response_proto import tests_pb2
from grr_response_server.instant_output_plugins import sqlite_instant_plugin
from grr_response_server.output_plugins import test_plugins
from grr.test_lib import export_test_lib
from grr.test_lib import test_lib


class SqliteInstantOutputPluginProtoTest(
    test_plugins.InstantOutputPluginTestBase
):
  """Tests the SQLite instant output plugin."""

  plugin_cls = sqlite_instant_plugin.SqliteInstantOutputPluginProto

  def ProcessValuesToZip(self, values_by_cls):
    fd_path = self.ProcessValuesProto(values_by_cls)
    file_basename, _ = os.path.splitext(os.path.basename(fd_path))
    return zipfile.ZipFile(fd_path), file_basename

  def setUp(self):
    super().setUp()
    # We use an in-memory db for testing generated SQL scripts.
    self.db_connection = sqlite3.connect(":memory:")
    self.db_cursor = self.db_connection.cursor()
    self.addCleanup(self.db_connection.close)

  def testConversionToCanonicalSqlDictWithVariousTypes(self):
    plugin = sqlite_instant_plugin.SqliteInstantOutputPluginProto(
        source_urn="aff4:/C.1000000000000000"
    )

    input_proto = tests_pb2.SampleGetHandlerArgs(
        path="foo",
        foo="bar",
        inner=tests_pb2.SampleInnerMessage(
            foo="inner_foo",
            bar=42,
            baz=True,
            # Protos should be FLAT here (lists are not really expected).
            fruits=[
                tests_pb2.SampleInnerMessage.Fruit.ACEROLA,
                tests_pb2.SampleInnerMessage.Fruit.JABUTICABA,
            ],
        ),
    )

    schema = plugin._GetSqliteSchema(input_proto.DESCRIPTOR)
    sql_dict = plugin._ConvertToCanonicalSqlDict(schema, input_proto)

    self.assertEqual(
        sql_dict,
        {
            "path": "foo",
            "foo": "bar",
            "inner.foo": "inner_foo",
            "inner.bar": 42,
            "inner.baz": 1,
            # Protos should be FLAT here (lists are not really expected).
            "inner.fruits": "[0, 1]",
        },
    )

  def testConversionToCanonicalSqlDictWithCyclicalStructures(self):
    plugin = sqlite_instant_plugin.SqliteInstantOutputPluginProto(
        source_urn="aff4:/C.1000000000000000"
    )

    input_proto = tests_pb2.MetadataTypesHierarchyRoot()
    input_proto.field_int64 = 123
    input_proto.child_2.field_string = "e"
    input_proto.child_1.child_1.field_string = "d"
    input_proto.child_1.root.field_int64 = 456
    input_proto.child_1.root.child_2.field_string = "c"
    input_proto.child_1.root.child_1.child_1.field_string = "b"
    input_proto.child_1.root.child_1.root.field_int64 = 789
    input_proto.child_1.root.child_1.root.child_2.field_string = "a"

    with self.assertRaises(RecursionError):
      schema = plugin._GetSqliteSchema(input_proto.DESCRIPTOR)
      plugin._ConvertToCanonicalSqlDict(schema, input_proto)

  @export_test_lib.WithAllExportConverters
  def testExportedFilenamesAndManifestForValuesOfSameType(self):
    responses = []
    for i in range(10):
      responses.append(
          jobs_pb2.StatEntry(
              pathspec=jobs_pb2.PathSpec(path=f"/foo/bar/{i}", pathtype="OS"),
              st_mode=33184,  # octal = 100640 => u=rw,g=r,o= => -rw-r-----
              st_ino=1063090,
              st_dev=64512,
              st_nlink=1 + i,
              st_uid=139592,
              st_gid=5000,
              st_size=0,
              st_atime=1493596800,
              st_mtime=1493683200,
              st_ctime=1493683200,
          )
      )

    zip_fd, prefix = self.ProcessValuesToZip(
        {jobs_pb2.StatEntry: responses}
    )
    self.assertEqual(
        set(zip_fd.namelist()),
        {f"{prefix}/MANIFEST",
         f"{prefix}/ExportedFile_from_StatEntry.sql"},
    )
    parsed_manifest = yaml.safe_load(zip_fd.read(f"{prefix}/MANIFEST"))
    self.assertEqual(
        parsed_manifest, {"export_stats": {"StatEntry": {"ExportedFile": 10}}}
    )

  @export_test_lib.WithAllExportConverters
  def testExportedTableStructureForValuesOfSameType(self):
    responses = []
    for i in range(10):
      responses.append(
          jobs_pb2.StatEntry(
              pathspec=jobs_pb2.PathSpec(path="/foo/bar/%d" % i, pathtype="OS"),
              st_mode=33184,  # octal = 100640 => u=rw,g=r,o= => -rw-r-----
              st_ino=1063090,
              st_dev=64512,
              st_nlink=1 + i,
              st_uid=139592,
              st_gid=5000,
              st_size=0,
              st_atime=1493596800,
              st_mtime=1493683200,
              st_ctime=1493683200,
          )
      )

    zip_fd, prefix = self.ProcessValuesToZip(
        {jobs_pb2.StatEntry: responses}
    )

    sqlite_dump_path = f"{prefix}/ExportedFile_from_StatEntry.sql"
    sqlite_dump = zip_fd.read(sqlite_dump_path).decode("utf-8")

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
    columns = [row[1] for row in self.db_cursor.fetchall()]
    expected_columns = [
        "metadata.client_urn",
        "metadata.client_id",
        "metadata.hostname",
        "metadata.os",
        "metadata.client_age",
        "metadata.os_release",
        "metadata.os_version",
        "metadata.usernames",
        "metadata.mac_address",
        "metadata.timestamp",
        "metadata.deprecated_session_id",
        "metadata.labels",
        "metadata.system_labels",
        "metadata.user_labels",
        "metadata.source_urn",
        "metadata.annotations",
        "metadata.hardware_info.serial_number",
        "metadata.hardware_info.system_manufacturer",
        "metadata.hardware_info.system_product_name",
        "metadata.hardware_info.system_uuid",
        "metadata.hardware_info.system_sku_number",
        "metadata.hardware_info.system_family",
        "metadata.hardware_info.bios_vendor",
        "metadata.hardware_info.bios_version",
        "metadata.hardware_info.bios_release_date",
        "metadata.hardware_info.bios_rom_size",
        "metadata.hardware_info.bios_revision",
        "metadata.hardware_info.system_assettag",
        "metadata.kernel_version",
        "metadata.cloud_instance_type",
        "metadata.cloud_instance_id",
        "urn",
        "basename",
        "st_mode",
        "st_ino",
        "st_dev",
        "st_nlink",
        "st_uid",
        "st_gid",
        "st_size",
        "st_atime",
        "st_mtime",
        "st_ctime",
        "st_btime",
        "st_blocks",
        "st_blksize",
        "st_rdev",
        "symlink",
        "content",
        "content_sha256",
        "hash_md5",
        "hash_sha1",
        "hash_sha256",
        "pecoff_hash_md5",
        "pecoff_hash_sha1",
        "cert_hasher_name",
        "cert_program_name",
        "cert_program_url",
        "cert_signing_id",
        "cert_chain_head_issuer",
        "cert_countersignature_chain_head_issuer",
        "cert_certificates",
    ]
    self.assertCountEqual(columns, expected_columns)

  @export_test_lib.WithAllExportConverters
  def testExportedRowsForValuesOfSameType(self):
    responses = []
    for i in range(10):
      responses.append(
          jobs_pb2.StatEntry(
              pathspec=jobs_pb2.PathSpec(path="/foo/bar/%d" % i, pathtype="OS"),
              st_mode=33184,  # octal = 100640 => u=rw,g=r,o= => -rw-r-----
              st_ino=1063090,
              st_dev=64512,
              st_nlink=1 + i,
              st_uid=139592,
              st_gid=5000,
              st_size=0,
              st_atime=1493596800,
              st_mtime=1493683200,
              st_ctime=1493683200,
          )
      )

    zip_fd, prefix = self.ProcessValuesToZip(
        {jobs_pb2.StatEntry: responses}
    )

    sqlite_dump_path = "%s/ExportedFile_from_StatEntry.sql" % prefix
    sqlite_dump = zip_fd.read(sqlite_dump_path).decode("utf-8")

    # Import the sql dump into an in-memory db.
    with self.db_connection:
      self.db_cursor.executescript(sqlite_dump)

    select_columns = [
        "metadata.client_urn",
        "metadata.source_urn",
        "urn",
        "st_mode",
        "st_ino",
        "st_dev",
        "st_nlink",
        "st_uid",
        "st_gid",
        "st_size",
        "st_atime",
        "st_mtime",
        "st_ctime",
        "st_blksize",
        "st_rdev",
        "symlink",
    ]
    escaped_column_names = ['"%s"' % c for c in select_columns]
    self.db_cursor.execute(
        'SELECT %s FROM "ExportedFile.from_StatEntry";'
        % ",".join(escaped_column_names)
    )
    rows = self.db_cursor.fetchall()
    self.assertLen(rows, 10)
    for i, row in enumerate(rows):
      results = {k: row[j] for j, k in enumerate(select_columns)}
      expected_results = {
          "metadata.client_urn": f"aff4:/{self.client_id}",
          "metadata.source_urn": str(self.results_urn),
          "urn": f"aff4:/{self.client_id}/fs/os/foo/bar/{i}",
          "st_mode": 33184,
          "st_ino": 1063090,
          "st_dev": 64512,
          "st_nlink": i + 1,
          "st_uid": 139592,
          "st_gid": 5000,
          "st_size": 0,
          "st_atime": 1493596800,
          "st_mtime": 1493683200,
          "st_ctime": 1493683200,
          "st_blksize": 0,
          "st_rdev": 0,
          "symlink": "",
      }
      self.assertEqual(results, expected_results)

  @export_test_lib.WithAllExportConverters
  def testExportedFilenamesAndManifestForValuesOfMultipleTypes(self):
    zip_fd, prefix = self.ProcessValuesToZip({
        jobs_pb2.StatEntry: [
            jobs_pb2.StatEntry(
                pathspec=jobs_pb2.PathSpec(path="/foo/bar", pathtype="OS")
            )
        ],
        sysinfo_pb2.Process: [sysinfo_pb2.Process(pid=42)],
    })
    self.assertEqual(
        set(zip_fd.namelist()),
        {
            f"{prefix}/MANIFEST",
            f"{prefix}/ExportedFile_from_StatEntry.sql",
            f"{prefix}/ExportedProcess_from_Process.sql",
        },
    )

    parsed_manifest = yaml.safe_load(zip_fd.read(f"{prefix}/MANIFEST"))
    self.assertEqual(
        parsed_manifest,
        {
            "export_stats": {
                "StatEntry": {"ExportedFile": 1},
                "Process": {"ExportedProcess": 1},
            }
        },
    )

  @export_test_lib.WithAllExportConverters
  def testExportedRowsForValuesOfMultipleTypes(self):
    zip_fd, prefix = self.ProcessValuesToZip({
        jobs_pb2.StatEntry: [
            jobs_pb2.StatEntry(
                pathspec=jobs_pb2.PathSpec(path="/foo/bar", pathtype="OS")
            )
        ],
        sysinfo_pb2.Process: [sysinfo_pb2.Process(pid=42)],
    })
    with self.db_connection:
      stat_entry_script_path = "%s/ExportedFile_from_StatEntry.sql" % prefix
      stat_entry_script = zip_fd.read(stat_entry_script_path).decode("utf-8")

      process_script_path = "%s/ExportedProcess_from_Process.sql" % prefix
      process_script = zip_fd.read(process_script_path).decode("utf-8")

      self.db_cursor.executescript(stat_entry_script)
      self.db_cursor.executescript(process_script)

    self.db_cursor.execute(
        'SELECT "metadata.client_urn", "metadata.source_urn", urn '
        'FROM "ExportedFile.from_StatEntry";'
    )
    stat_entry_results = self.db_cursor.fetchall()
    self.assertLen(stat_entry_results, 1)
    # Client URN
    self.assertEqual(stat_entry_results[0][0], f"aff4:/{self.client_id}")
    # Source URN
    self.assertEqual(stat_entry_results[0][1], str(self.results_urn))
    # URN
    self.assertEqual(
        stat_entry_results[0][2], f"aff4:/{self.client_id}/fs/os/foo/bar"
    )

    self.db_cursor.execute(
        'SELECT "metadata.client_urn", "metadata.source_urn", pid '
        'FROM "ExportedProcess.from_Process";'
    )
    process_results = self.db_cursor.fetchall()
    self.assertLen(process_results, 1)
    # Client URN
    self.assertEqual(stat_entry_results[0][0], f"aff4:/{self.client_id}")
    # Source URN
    self.assertEqual(process_results[0][1], str(self.results_urn))
    # PID
    self.assertEqual(process_results[0][2], 42)

  @export_test_lib.WithAllExportConverters
  def testHandlingOfNonAsciiCharacters(self):
    zip_fd, prefix = self.ProcessValuesToZip({
        jobs_pb2.StatEntry: [
            jobs_pb2.StatEntry(
                pathspec=jobs_pb2.PathSpec(
                    path="/中国新闻网新闻中", pathtype="OS"
                )
            )
        ]
    })
    self.assertEqual(
        set(zip_fd.namelist()),
        {f"{prefix}/MANIFEST", f"{prefix}/ExportedFile_from_StatEntry.sql"},
    )

    with self.db_connection:
      sqlite_dump_path = "%s/ExportedFile_from_StatEntry.sql" % prefix
      sqlite_dump = zip_fd.read(sqlite_dump_path).decode("utf-8")
      self.db_cursor.executescript(sqlite_dump)

    self.db_cursor.execute('SELECT urn FROM "ExportedFile.from_StatEntry";')
    results = self.db_cursor.fetchall()
    self.assertLen(results, 1)
    self.assertEqual(
        results[0][0], f"aff4:/{self.client_id}/fs/os/中国新闻网新闻中"
    )

  @export_test_lib.WithAllExportConverters
  def testHandlingOfMultipleRowBatches(self):
    num_rows = self.__class__.plugin_cls.ROW_BATCH * 2 + 1

    responses = []
    for i in range(num_rows):
      responses.append(
          jobs_pb2.StatEntry(
              pathspec=jobs_pb2.PathSpec(path=f"/foo/bar/{i}", pathtype="OS")
          )
      )

    zip_fd, prefix = self.ProcessValuesToZip(
        {jobs_pb2.StatEntry: responses}
    )
    with self.db_connection:
      sqlite_dump_path = f"{prefix}/ExportedFile_from_StatEntry.sql"
      sqlite_dump = zip_fd.read(sqlite_dump_path).decode("utf-8")
      self.db_cursor.executescript(sqlite_dump)
    self.db_cursor.execute('SELECT urn FROM "ExportedFile.from_StatEntry";')
    results = self.db_cursor.fetchall()
    self.assertLen(results, num_rows)
    for i in range(num_rows):
      self.assertEqual(
          results[i][0], f"aff4:/{self.client_id}/fs/os/foo/bar/{i}"
      )


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
