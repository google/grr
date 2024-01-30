#!/usr/bin/env python
"""Program that generates golden regression data."""

import contextlib

from absl import app

from grr_response_server.databases import mysql_migration
from grr_response_server.databases import mysql_test
from grr.test_lib import testing_startup


def main(argv):
  """Entry function."""
  del argv
  testing_startup.TestInit()

  test_db = mysql_test.TestMysqlDB()
  test_db.__class__.setUpClass()
  try:
    db, cleanup_fn = test_db.CreateDatabase()
    # Safe to ignore here, since this cleanup function will be called by
    # `tearDownClass()`
    del cleanup_fn

    def _DumpSchema(conn):
      with contextlib.closing(conn.cursor()) as cursor:
        return mysql_migration.DumpCurrentSchema(cursor)

    schema = db._RunInTransaction(_DumpSchema)  # pylint: disable=protected-access
    print(schema)
  finally:
    test_db.__class__.tearDownClass()


def DistEntry():
  """The main entry point for packages."""
  app.run(main)


if __name__ == "__main__":
  app.run(main)
