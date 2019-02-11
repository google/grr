#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""A module with client action for talking with osquery."""
from __future__ import absolute_import
from __future__ import division

from __future__ import unicode_literals

import binascii
import collections
import datetime
import hashlib
import io
import os
import socket
import unittest

from absl import flags
from absl.testing import absltest
from future.builtins import str
from typing import List
from typing import Text

from grr_response_client.client_actions import osquery
from grr_response_core import config
from grr_response_core.lib.rdfvalues import osquery as rdf_osquery
from grr_response_core.lib.util import filesystem
from grr_response_core.lib.util import temp

FLAGS = flags.FLAGS


def _Query(query):
  return _Queries([query])


def _Queries(queries):
  args = rdf_osquery.OsqueryArgs(queries=queries)
  return list(osquery.Osquery().Run(args))[0]


class OsqueryTest(absltest.TestCase):

  @classmethod
  def setUpClass(cls):
    if not config.CONFIG.initialized:
      config.CONFIG.Initialize(FLAGS.config)

    if not config.CONFIG["Osquery.path"]:
      raise unittest.SkipTest("`osquery_path` not specified")

    # TODO: `skipTest` has to execute before `setUpClass`.
    super(OsqueryTest, cls).setUpClass()

  def testNoQueries(self):
    result = _Queries([])
    self.assertEmpty(result.tables)

  def testPid(self):
    result = _Query("""
        SELECT * FROM processes WHERE pid = {};
    """.format(os.getpid()))

    self.assertLen(result.tables, 1)
    self.assertEqual(list(result.tables[0].Column("pid")), [str(os.getpid())])

  def testHash(self):
    with temp.AutoTempFilePath() as filepath:
      content = b"foobarbaz"
      md5 = binascii.hexlify(hashlib.md5(content).digest())
      sha256 = binascii.hexlify(hashlib.sha256(content).digest())

      with io.open(filepath, "wb") as filedesc:
        filedesc.write(content)

      result = _Query("""
        SELECT md5, sha256 FROM hash WHERE path = "{}";
      """.format(filepath))

      self.assertLen(result.tables, 1)
      self.assertEqual(list(result.tables[0].Column("md5")), [md5])
      self.assertEqual(list(result.tables[0].Column("sha256")), [sha256])

  def testFile(self):
    with temp.AutoTempDirPath(remove_non_empty=True) as dirpath:
      with io.open(os.path.join(dirpath, "abc"), "wb") as filedesc:
        filedesc.write(b"FOO")

      with io.open(os.path.join(dirpath, "def"), "wb") as filedesc:
        filedesc.write(b"BARBAZ")

      with io.open(os.path.join(dirpath, "ghi"), "wb") as filedesc:
        filedesc.write(b"QUUX")

      result = _Query("""
        SELECT * FROM file WHERE directory = "{}" ORDER BY path;
      """.format(dirpath))

      self.assertLen(result.tables, 1)
      self.assertLen(result.tables[0].rows, 3)
      self.assertEqual(
          list(result.tables[0].Column("path")), [
              os.path.join(dirpath, "abc"),
              os.path.join(dirpath, "def"),
              os.path.join(dirpath, "ghi"),
          ])
      self.assertEqual(list(result.tables[0].Column("size")), ["3", "6", "4"])

  def testFileUnicode(self):
    with temp.AutoTempFilePath(prefix="zółć", suffix="💰") as filepath:
      with io.open(filepath, "wb") as filedesc:
        filedesc.write(b"FOOBAR")

      stat = filesystem.Stat(filepath)
      atime = stat.GetAccessTime()
      mtime = stat.GetModificationTime()
      ctime = stat.GetChangeTime()
      size = stat.GetSize()

      result = _Query("""
        SELECT * FROM file WHERE path = "{}";
      """.format(filepath))

      self.assertLen(result.tables, 1)

      table = result.tables[0]
      self.assertLen(table.rows, 1)
      self.assertEqual(list(table.Column("path")), [filepath])
      self.assertEqual(list(table.Column("atime")), [str(atime)])
      self.assertEqual(list(table.Column("mtime")), [str(mtime)])
      self.assertEqual(list(table.Column("ctime")), [str(ctime)])
      self.assertEqual(list(table.Column("size")), [str(size)])

  def testIncorrectQuery(self):
    with self.assertRaises(RuntimeError):
      _Query("FROM foo SELECT bar;")

  def testTimeAndSystemInfo(self):
    date_before = datetime.date.today()

    result = _Queries([
        "SELECT year, month, day FROM time;",
        "SELECT hostname FROM system_info;",
    ])

    date_after = datetime.date.today()

    self.assertLen(result.tables, 2)
    time_table = result.tables[0]
    sysinfo_table = result.tables[1]

    self.assertLen(time_table.rows, 1)

    date_result = datetime.date(
        year=int(list(time_table.Column("year"))[0]),
        month=int(list(time_table.Column("month"))[0]),
        day=int(list(time_table.Column("day"))[0]))
    self.assertBetween(date_result, date_before, date_after)

    hostname = socket.gethostname()

    self.assertLen(sysinfo_table.rows, 1)
    self.assertEqual(list(sysinfo_table.Column("hostname")), [hostname])


class ParseTableTest(absltest.TestCase):

  def testEmpty(self):
    table = osquery.ParseTable([])
    self.assertEmpty(table.header.columns)
    self.assertEmpty(table.rows)

  def testSingleRow(self):
    row = collections.OrderedDict()
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
    row0 = collections.OrderedDict()
    row0["A"] = "foo"
    row0["B"] = "bar"
    row0["C"] = "baz"

    row1 = collections.OrderedDict()
    row1["A"] = "quux"
    row1["B"] = "norf"
    row1["C"] = "thud"

    row2 = collections.OrderedDict()
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
    row0 = collections.OrderedDict()
    row0["A"] = "foo"
    row0["B"] = "bar"

    row1 = collections.OrderedDict()
    row1["A"] = "quux"
    row1["C"] = "thud"

    with self.assertRaises(ValueError):
      osquery.ParseTable([row0, row1])


class ParseHeaderTest(absltest.TestCase):

  def testEmpty(self):
    header = osquery.ParseHeader([])
    self.assertEmpty(header.columns, 0)

  def testSingleRow(self):
    row = collections.OrderedDict()
    row["foo"] = "quux"
    row["bar"] = "thud"
    row["baz"] = "norf"

    header = osquery.ParseHeader([row])

    self.assertLen(header.columns, 3)
    self.assertEqual(header.columns[0].name, "foo")
    self.assertEqual(header.columns[1].name, "bar")
    self.assertEqual(header.columns[2].name, "baz")

  def testMultiRow(self):
    row0 = collections.OrderedDict()
    row0["foo"] = "quux"
    row0["bar"] = "thud"
    row0["baz"] = "norf"

    row1 = collections.OrderedDict()
    row1["foo"] = "blargh"
    row1["bar"] = "plugh"
    row1["baz"] = "ztesch"

    header = osquery.ParseHeader([row0, row1])

    self.assertLen(header.columns, 3)
    self.assertEqual(header.columns[0].name, "foo")
    self.assertEqual(header.columns[1].name, "bar")
    self.assertEqual(header.columns[2].name, "baz")

  def testIncompatibleRows(self):
    row0 = collections.OrderedDict()
    row0["foo"] = "quux"
    row0["bar"] = "thud"

    row1 = collections.OrderedDict()
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

    row = osquery.ParseRow(header, {
        "foo": "quux",
        "bar": "norf",
        "baz": "thud",
    })
    self.assertEqual(row.values, ["quux", "norf", "thud"])


if __name__ == "__main__":
  absltest.main()
