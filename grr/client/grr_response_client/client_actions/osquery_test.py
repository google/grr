#!/usr/bin/env python
"""A module with client action for talking with osquery."""

import hashlib
import io
import json
import os
import platform
import socket
import time

from absl import flags
from absl.testing import absltest

from grr_response_client.client_actions import osquery
from grr_response_core import config
from grr_response_core.lib.rdfvalues import osquery as rdf_osquery
from grr_response_core.lib.util import filesystem
from grr_response_core.lib.util import temp
from grr_response_core.lib.util import text
from grr.test_lib import osquery_test_lib
from grr.test_lib import skip
from grr.test_lib import test_lib

FLAGS = flags.FLAGS


def _Query(query: str, **kwargs) -> list[rdf_osquery.OsqueryResult]:
  args = rdf_osquery.OsqueryArgs(query=query, **kwargs)
  return list(osquery.Osquery().Process(args))


@skip.Unless(
    lambda: config.CONFIG["Osquery.path"], "osquery path not specified"
)
class OsqueryTest(absltest.TestCase):

  @classmethod
  def setUpClass(cls):
    super(OsqueryTest, cls).setUpClass()
    if not config.CONFIG.initialized:
      config.CONFIG.Initialize(FLAGS.config)

  def testConfigurationArgError(self):
    with self.assertRaises(ValueError):
      args = rdf_osquery.OsqueryArgs(
          query="SELECT bar FROM foo;", configuration_path="bar"
      )
      _ = list(osquery.Osquery().Process(args))

  def testConfigurationContent(self):
    configuration_content = json.dumps(
        {"views": {"bar": "SELECT * FROM processes;"}}
    )

    args = rdf_osquery.OsqueryArgs(
        query="SELECT * FROM bar where pid = {};".format(os.getpid()),
        configuration_content=configuration_content,
    )
    results = list(osquery.Osquery().Process(args))
    self.assertLen(results, 1)

    table = results[0].table
    self.assertEqual(list(table.Column("pid")), [str(os.getpid())])

  def testConfigurationPath(self):
    with temp.AutoTempFilePath() as configuration_path:
      configuration_content = json.dumps(
          {"views": {"bar": "SELECT * FROM processes;"}}
      )

      with io.open(configuration_path, "wt") as config_handle:
        config_handle.write(configuration_content)

      args = rdf_osquery.OsqueryArgs(
          query="SELECT * FROM bar where pid = {};".format(os.getpid()),
          configuration_path=configuration_path,
      )
      results = list(osquery.Osquery().Process(args))
      self.assertLen(results, 1)

      table = results[0].table
      self.assertEqual(list(table.Column("pid")), [str(os.getpid())])

  def testPid(self):
    results = _Query("""
        SELECT * FROM processes WHERE pid = {};
    """.format(os.getpid()))
    self.assertLen(results, 1)

    table = results[0].table
    self.assertEqual(list(table.Column("pid")), [str(os.getpid())])

  def testHash(self):
    with temp.AutoTempFilePath() as filepath:
      content = b"foobarbaz"

      md5_digest = hashlib.md5(content).digest()
      sha256_digest = hashlib.sha256(content).digest()

      md5 = text.Hexify(md5_digest)
      sha256 = text.Hexify(sha256_digest)

      with io.open(filepath, "wb") as filedesc:
        filedesc.write(content)

      results = _Query("""
        SELECT md5, sha256 FROM hash WHERE path = "{}";
      """.format(filepath))
      self.assertLen(results, 1)

      table = results[0].table
      self.assertEqual(list(table.Column("md5")), [md5])
      self.assertEqual(list(table.Column("sha256")), [sha256])

  def testFile(self):
    with temp.AutoTempDirPath(remove_non_empty=True) as dirpath:
      with io.open(os.path.join(dirpath, "abc"), "wb") as filedesc:
        filedesc.write(b"FOO")

      with io.open(os.path.join(dirpath, "def"), "wb") as filedesc:
        filedesc.write(b"BARBAZ")

      with io.open(os.path.join(dirpath, "ghi"), "wb") as filedesc:
        filedesc.write(b"QUUX")

      results = _Query("""
        SELECT * FROM file WHERE directory = "{}" ORDER BY path;
      """.format(dirpath))
      self.assertLen(results, 1)

      table = results[0].table
      self.assertLen(table.rows, 3)
      self.assertEqual(
          list(table.Column("path")),
          [
              os.path.join(dirpath, "abc"),
              os.path.join(dirpath, "def"),
              os.path.join(dirpath, "ghi"),
          ],
      )
      self.assertEqual(list(table.Column("size")), ["3", "6", "4"])

  # TODO(hanuszczak): https://github.com/osquery/osquery/issues/4150
  @skip.If(
      platform.system() == "Windows",
      "osquery ignores files with unicode characters.",
  )
  def testFileUnicode(self):
    with temp.AutoTempFilePath(prefix="zółć", suffix="💰") as filepath:
      with io.open(filepath, "wb") as filedesc:
        filedesc.write(b"FOOBAR")

      stat = filesystem.Stat.FromPath(filepath)
      atime = stat.GetAccessTime() // 1000000
      mtime = stat.GetModificationTime() // 1000000
      ctime = stat.GetChangeTime() // 1000000
      size = stat.GetSize()

      results = _Query("""
        SELECT * FROM file WHERE path = "{}";
      """.format(filepath))
      self.assertLen(results, 1)

      table = results[0].table
      self.assertLen(table.rows, 1)
      self.assertEqual(list(table.Column("path")), [filepath])
      self.assertEqual(list(table.Column("atime")), [str(atime)])
      self.assertEqual(list(table.Column("mtime")), [str(mtime)])
      self.assertEqual(list(table.Column("ctime")), [str(ctime)])
      self.assertEqual(list(table.Column("size")), [str(size)])

  def testIncorrectQuery(self):
    with self.assertRaises(osquery.Error):
      _Query("FROM foo SELECT bar;")

  def testEmptyQuery(self):
    with self.assertRaises(ValueError):
      _Query("")

  def testTime(self):
    time_before = int(time.time())
    results = _Query("SELECT unix_time FROM time;")
    time_after = int(time.time())
    self.assertLen(results, 1)

    table = results[0].table
    self.assertLen(table.rows, 1)

    time_result = int(list(table.Column("unix_time"))[0])
    self.assertBetween(time_result, time_before, time_after)

  def testTimeout(self):
    with self.assertRaises(osquery.TimeoutError):
      _Query("SELECT * FROM processes;", timeout_millis=0)

  def testSystemInfo(self):
    results = _Query("SELECT hostname FROM system_info;")
    self.assertLen(results, 1)

    table = results[0].table
    self.assertLen(table.rows, 1)

    # osquery sometimes returns FQDN and sometimes real hostname as the result
    # and it is unclear what determines this. This is why instead of precise
    # equality we test for either of them.
    hostname = list(table.Column("hostname"))[0]
    self.assertIn(hostname, [socket.gethostname(), socket.getfqdn()])

  def testMultipleResults(self):
    with temp.AutoTempDirPath(remove_non_empty=True) as dirpath:
      with io.open(os.path.join(dirpath, "foo"), "wb") as filedesc:
        del filedesc  # Unused.
      with io.open(os.path.join(dirpath, "bar"), "wb") as filedesc:
        del filedesc  # Unused.
      with io.open(os.path.join(dirpath, "baz"), "wb") as filedesc:
        del filedesc  # Unused.

      query = """
        SELECT filename FROM file
        WHERE directory = "{}"
        ORDER BY filename;
      """.format(dirpath)

      with test_lib.ConfigOverrider({"Osquery.max_chunk_size": 3}):
        results = _Query(query)

      self.assertLen(results, 3)

      for result in results:
        self.assertEqual(result.table.query, query)
        self.assertLen(result.table.header.columns, 1)
        self.assertEqual(result.table.header.columns[0].name, "filename")

      self.assertEqual(list(results[0].table.Column("filename")), ["bar"])
      self.assertEqual(list(results[1].table.Column("filename")), ["baz"])
      self.assertEqual(list(results[2].table.Column("filename")), ["foo"])


class FakeOsqueryTest(absltest.TestCase):

  @classmethod
  def setUpClass(cls):
    super(FakeOsqueryTest, cls).setUpClass()
    if not config.CONFIG.initialized:
      config.CONFIG.Initialize(FLAGS.config)

  def testOutput(self):
    stdout = """
    [
      { "foo": "bar", "quux": "norf" },
      { "foo": "baz", "quux": "thud" }
    ]
    """
    with osquery_test_lib.FakeOsqueryiOutput(stdout=stdout, stderr=""):
      results = _Query("SELECT foo, quux FROM blargh;")

    self.assertLen(results, 1)

    table = results[0].table
    self.assertLen(table.header.columns, 2)
    self.assertEqual(table.header.columns[0].name, "foo")
    self.assertEqual(table.header.columns[1].name, "quux")
    self.assertEqual(list(table.Column("foo")), ["bar", "baz"])
    self.assertEqual(list(table.Column("quux")), ["norf", "thud"])

  def testErrorOutput(self):
    stderr = "Error: near 'FROM': syntax error"
    with osquery_test_lib.FakeOsqueryiOutput(stdout="", stderr=stderr):
      with self.assertRaises(osquery.Error) as context:
        _Query("FROM bar SELECT foo;")

    self.assertIn(stderr, str(context.exception))

  def testErrorCode(self):
    stderr = "Error: permission error"
    with osquery_test_lib.FakeOsqueryiError(stderr=stderr):
      with self.assertRaises(osquery.Error) as context:
        _Query("SELECT * FROM processes;")

    self.assertIn(stderr, str(context.exception))

  def testTimeout(self):
    with osquery_test_lib.FakeOsqueryiSleep(1.0):
      with self.assertRaises(osquery.TimeoutError):
        _Query("SELECT * FROM processes;", timeout_millis=0)


class ChunkTableTest(absltest.TestCase):

  def testNoRows(self):
    table = rdf_osquery.OsqueryTable()
    table.header.columns.append(rdf_osquery.OsqueryColumn(name="foo"))
    table.header.columns.append(rdf_osquery.OsqueryColumn(name="bar"))
    table.query = "SELECT * FROM quux;"

    chunks = list(osquery.ChunkTable(table, max_chunk_size=1024 * 1024 * 1024))
    self.assertEmpty(chunks)

  def testSingleRowChunks(self):
    table = rdf_osquery.OsqueryTable()
    table.query = "SELECT foo, bar, baz FROM quux;"
    table.header.columns.append(rdf_osquery.OsqueryColumn(name="foo"))
    table.header.columns.append(rdf_osquery.OsqueryColumn(name="bar"))
    table.header.columns.append(rdf_osquery.OsqueryColumn(name="baz"))
    table.rows.append(rdf_osquery.OsqueryRow(values=["ABC", "DEF", "GHI"]))
    table.rows.append(rdf_osquery.OsqueryRow(values=["JKL", "MNO", "PQR"]))
    table.rows.append(rdf_osquery.OsqueryRow(values=["RST", "UVW", "XYZ"]))

    chunks = list(osquery.ChunkTable(table, max_chunk_size=9))
    self.assertLen(chunks, 3)
    self.assertEqual(chunks[0].query, table.query)
    self.assertEqual(chunks[0].header, table.header)
    self.assertEqual(
        chunks[0].rows,
        [
            rdf_osquery.OsqueryRow(values=["ABC", "DEF", "GHI"]),
        ],
    )
    self.assertEqual(chunks[1].query, table.query)
    self.assertEqual(chunks[1].header, table.header)
    self.assertEqual(
        chunks[1].rows,
        [
            rdf_osquery.OsqueryRow(values=["JKL", "MNO", "PQR"]),
        ],
    )
    self.assertEqual(chunks[2].query, table.query)
    self.assertEqual(chunks[2].header, table.header)
    self.assertEqual(
        chunks[2].rows,
        [
            rdf_osquery.OsqueryRow(values=["RST", "UVW", "XYZ"]),
        ],
    )

  def testMultiRowChunks(self):
    table = rdf_osquery.OsqueryTable()
    table.query = "SELECT foo, bar, baz FROM quux;"
    table.header.columns.append(rdf_osquery.OsqueryColumn(name="foo"))
    table.header.columns.append(rdf_osquery.OsqueryColumn(name="bar"))
    table.header.columns.append(rdf_osquery.OsqueryColumn(name="baz"))
    table.rows.append(rdf_osquery.OsqueryRow(values=["A", "B", "C"]))
    table.rows.append(rdf_osquery.OsqueryRow(values=["D", "E", "F"]))
    table.rows.append(rdf_osquery.OsqueryRow(values=["G", "H", "I"]))
    table.rows.append(rdf_osquery.OsqueryRow(values=["J", "K", "L"]))
    table.rows.append(rdf_osquery.OsqueryRow(values=["M", "N", "O"]))
    table.rows.append(rdf_osquery.OsqueryRow(values=["P", "Q", "R"]))
    table.rows.append(rdf_osquery.OsqueryRow(values=["S", "T", "U"]))
    table.rows.append(rdf_osquery.OsqueryRow(values=["V", "W", "X"]))

    chunks = list(osquery.ChunkTable(table, max_chunk_size=10))
    self.assertLen(chunks, 3)
    self.assertEqual(chunks[0].query, table.query)
    self.assertEqual(chunks[0].header, table.header)
    self.assertEqual(
        chunks[0].rows,
        [
            rdf_osquery.OsqueryRow(values=["A", "B", "C"]),
            rdf_osquery.OsqueryRow(values=["D", "E", "F"]),
            rdf_osquery.OsqueryRow(values=["G", "H", "I"]),
        ],
    )
    self.assertEqual(chunks[1].query, table.query)
    self.assertEqual(chunks[1].header, table.header)
    self.assertEqual(
        chunks[1].rows,
        [
            rdf_osquery.OsqueryRow(values=["J", "K", "L"]),
            rdf_osquery.OsqueryRow(values=["M", "N", "O"]),
            rdf_osquery.OsqueryRow(values=["P", "Q", "R"]),
        ],
    )
    self.assertEqual(chunks[2].query, table.query)
    self.assertEqual(chunks[2].header, table.header)
    self.assertEqual(
        chunks[2].rows,
        [
            rdf_osquery.OsqueryRow(values=["S", "T", "U"]),
            rdf_osquery.OsqueryRow(values=["V", "W", "X"]),
        ],
    )

  def testMultiByteStrings(self):
    table = rdf_osquery.OsqueryTable()
    table.query = "SELECT foo, bar, baz FROM quux;"
    table.header.columns.append(rdf_osquery.OsqueryColumn(name="foo"))
    table.header.columns.append(rdf_osquery.OsqueryColumn(name="bar"))
    table.rows.append(rdf_osquery.OsqueryRow(values=["🐔", "🐓"]))
    table.rows.append(rdf_osquery.OsqueryRow(values=["🐣", "🐤"]))
    table.rows.append(rdf_osquery.OsqueryRow(values=["🐥", "🦆"]))

    chunks = list(osquery.ChunkTable(table, max_chunk_size=10))
    self.assertLen(chunks, 3)
    self.assertEqual(
        chunks[0].rows, [rdf_osquery.OsqueryRow(values=["🐔", "🐓"])]
    )
    self.assertEqual(
        chunks[1].rows, [rdf_osquery.OsqueryRow(values=["🐣", "🐤"])]
    )
    self.assertEqual(
        chunks[2].rows, [rdf_osquery.OsqueryRow(values=["🐥", "🦆"])]
    )


class ParseTableTest(absltest.TestCase):

  def testEmpty(self):
    table = osquery.ParseTable([])
    self.assertEmpty(table.header.columns)
    self.assertEmpty(table.rows)

  def testSingleRow(self):
    row = dict()
    row["foo"] = "quux"
    row["bar"] = "thud"
    row["baz"] = "norf"

    table = osquery.ParseTable([row])

    self.assertLen(table.header.columns, 3)
    self.assertEqual(table.header.columns[0].name, "foo")
    self.assertEqual(table.header.columns[1].name, "bar")
    self.assertEqual(table.header.columns[2].name, "baz")

    self.assertLen(table.rows, 1)
    self.assertEqual(table.rows[0].values, ["quux", "thud", "norf"])

  def testMultiRow(self):
    row0 = dict()
    row0["A"] = "foo"
    row0["B"] = "bar"
    row0["C"] = "baz"

    row1 = dict()
    row1["A"] = "quux"
    row1["B"] = "norf"
    row1["C"] = "thud"

    row2 = dict()
    row2["A"] = "blargh"
    row2["B"] = "plugh"
    row2["C"] = "ztesch"

    table = osquery.ParseTable([row0, row1, row2])

    self.assertLen(table.header.columns, 3)
    self.assertEqual(table.header.columns[0].name, "A")
    self.assertEqual(table.header.columns[1].name, "B")
    self.assertEqual(table.header.columns[2].name, "C")

    self.assertLen(table.rows, 3)
    self.assertEqual(table.rows[0].values, ["foo", "bar", "baz"])
    self.assertEqual(table.rows[1].values, ["quux", "norf", "thud"])
    self.assertEqual(table.rows[2].values, ["blargh", "plugh", "ztesch"])

  def testIncompatibleRows(self):
    row0 = dict()
    row0["A"] = "foo"
    row0["B"] = "bar"

    row1 = dict()
    row1["A"] = "quux"
    row1["C"] = "thud"

    with self.assertRaises(ValueError):
      osquery.ParseTable([row0, row1])


class ParseHeaderTest(absltest.TestCase):

  def testEmpty(self):
    header = osquery.ParseHeader([])
    self.assertEmpty(header.columns, 0)

  def testSingleRow(self):
    row = dict()
    row["foo"] = "quux"
    row["bar"] = "thud"
    row["baz"] = "norf"

    header = osquery.ParseHeader([row])

    self.assertLen(header.columns, 3)
    self.assertEqual(header.columns[0].name, "foo")
    self.assertEqual(header.columns[1].name, "bar")
    self.assertEqual(header.columns[2].name, "baz")

  def testMultiRow(self):
    row0 = dict()
    row0["foo"] = "quux"
    row0["bar"] = "thud"
    row0["baz"] = "norf"

    row1 = dict()
    row1["foo"] = "blargh"
    row1["bar"] = "plugh"
    row1["baz"] = "ztesch"

    header = osquery.ParseHeader([row0, row1])

    self.assertLen(header.columns, 3)
    self.assertEqual(header.columns[0].name, "foo")
    self.assertEqual(header.columns[1].name, "bar")
    self.assertEqual(header.columns[2].name, "baz")

  def testIncompatibleRows(self):
    row0 = dict()
    row0["foo"] = "quux"
    row0["bar"] = "thud"

    row1 = dict()
    row1["baz"] = "thud"
    row1["bar"] = "blargh"

    with self.assertRaises(ValueError):
      osquery.ParseHeader([row0, row1])


class ParseRowTest(absltest.TestCase):

  def testEmpty(self):
    header = rdf_osquery.OsqueryHeader()

    row = osquery.ParseRow(header, {})
    self.assertEqual(row.values, [])

  def testSimple(self):
    header = rdf_osquery.OsqueryHeader()
    header.columns.append(rdf_osquery.OsqueryColumn(name="foo"))
    header.columns.append(rdf_osquery.OsqueryColumn(name="bar"))
    header.columns.append(rdf_osquery.OsqueryColumn(name="baz"))

    row = osquery.ParseRow(
        header,
        {
            "foo": "quux",
            "bar": "norf",
            "baz": "thud",
        },
    )
    self.assertEqual(row.values, ["quux", "norf", "thud"])


if __name__ == "__main__":
  absltest.main()
