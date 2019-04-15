#!/usr/bin/env python
"""Program that generates golden regression data."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import contextlib

from absl import app

from grr_response_server.databases import mysql_migration
from grr_response_server.databases import mysql_test
from grr.test_lib import testing_startup


def main(argv):
  """Entry function."""
  del argv
  testing_startup.TestInit()

  mysql_test.TestMysqlDB.setUpClass()
  try:
    # TODO(user): refactor the code to not use protected methods.
    db, fin = mysql_test.TestMysqlDB._CreateDatabase()  # pylint: disable=protected-access
    try:

      def _DumpSchema(conn):
        with contextlib.closing(conn.cursor()) as cursor:
          return mysql_migration.DumpCurrentSchema(cursor)

      schema = db._RunInTransaction(_DumpSchema)  # pylint: disable=protected-access
      print(schema)
    finally:
      fin()

  finally:
    mysql_test.TestMysqlDB.tearDownClass()


def DistEntry():
  """The main entry point for packages."""
  app.run(main)


if __name__ == "__main__":
  app.run(main)
