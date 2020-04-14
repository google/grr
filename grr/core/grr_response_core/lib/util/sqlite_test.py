#!/usr/bin/env python
# Lint as: python3
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import contextlib
import io

from absl.testing import absltest
import sqlite3

from grr_response_core.lib.util import sqlite
from grr_response_core.lib.util import temp


class ConnectionContextTest(absltest.TestCase):

  def testQuerySingleColumn(self):
    with temp.AutoTempFilePath(suffix=".sqlite") as db_filepath:
      with contextlib.closing(sqlite3.connect(db_filepath)) as conn:
        with contextlib.closing(conn.cursor()) as cursor:
          cursor.execute("CREATE TABLE foo (bar TEXT)")
          cursor.execute("INSERT INTO foo VALUES ('quux'), ('norf'), ('thud')")

        conn.commit()

        context = sqlite.ConnectionContext(conn)
        results = list(context.Query("SELECT * FROM foo"))
        self.assertEqual(results, [("quux",), ("norf",), ("thud",)])

  def testQueryMultipleColumns(self):
    with temp.AutoTempFilePath(suffix=".sqlite") as db_filepath:
      with contextlib.closing(sqlite3.connect(db_filepath)) as conn:
        with contextlib.closing(conn.cursor()) as cursor:
          cursor.execute("CREATE TABLE foo (bar INTEGER, baz TEXT)")
          cursor.execute("INSERT INTO foo(bar, baz) VALUES (42, 'quux')")
          cursor.execute("INSERT INTO foo(bar, baz) VALUES (108, 'norf')")

        conn.commit()

        context = sqlite.ConnectionContext(conn)
        results = list(context.Query("SELECT bar, baz FROM foo"))
        self.assertEqual(results, [(42, "quux"), (108, "norf")])


class IOConnectionTest(absltest.TestCase):

  def testSmallDatabase(self):
    with temp.AutoTempFilePath(suffix=".sqlite") as db_filepath:
      with contextlib.closing(sqlite3.connect(db_filepath)) as conn:
        with contextlib.closing(conn.cursor()) as cursor:
          cursor.execute("CREATE TABLE foo (bar INTEGER, baz INTEGER)")
          cursor.execute("INSERT INTO foo(bar, baz) VALUES (1, 3), (3, 7)")

        conn.commit()

      with io.open(db_filepath, mode="rb") as db_filedesc:
        db_bytes = db_filedesc.read()

      with sqlite.IOConnection(io.BytesIO(db_bytes)) as context:
        results = list(context.Query("SELECT bar, baz FROM foo"))
        self.assertEqual(results, [(1, 3), (3, 7)])

  def testBigDatabase(self):
    blob = lambda sample: sample * 1024 * 1024

    with temp.AutoTempFilePath(suffix=".sqlite") as db_filepath:
      with contextlib.closing(sqlite3.connect(db_filepath)) as conn:
        with contextlib.closing(conn.cursor()) as cursor:
          cursor.execute("CREATE TABLE foo (bar BLOB)")
          cursor.execute("INSERT INTO foo(bar) VALUES (?)", (blob(b"A"),))
          cursor.execute("INSERT INTO foo(bar) VALUES (?)", (blob(b"B"),))
          cursor.execute("INSERT INTO foo(bar) VALUES (?)", (blob(b"C"),))

        conn.commit()

      with io.open(db_filepath, mode="rb") as db_filedesc:
        with sqlite.IOConnection(db_filedesc) as context:
          results = list(context.Query("SELECT bar FROM foo"))
          self.assertLen(results, 3)
          self.assertEqual(results[0], (blob(b"A"),))
          self.assertEqual(results[1], (blob(b"B"),))
          self.assertEqual(results[2], (blob(b"C"),))


if __name__ == "__main__":
  absltest.main()
