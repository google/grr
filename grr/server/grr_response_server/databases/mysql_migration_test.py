#!/usr/bin/env python
"""Tests for the MySQL migrations logic."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import contextlib
import io
import os
import shutil

from absl import app
from absl.testing import absltest

from grr_response_core import config
from grr_response_core.lib.util import temp
from grr_response_server.databases import mysql_migration
from grr_response_server.databases import mysql_test
from grr.test_lib import test_lib


class ListMigrationsToProcessTest(absltest.TestCase):

  def setUp(self):
    super(ListMigrationsToProcessTest, self).setUp()
    self.temp_dir = temp.TempDirPath()
    self.addCleanup(lambda: shutil.rmtree(self.temp_dir, ignore_errors=True))

  def _CreateMigrationFiles(self, fnames):
    for fname in fnames:
      with open(os.path.join(self.temp_dir, fname), "w"):
        pass

  def testReturnsAllMigrationsWhenCurrentNumberIsNone(self):
    fnames = ["0000.sql", "0001.sql", "0002.sql"]
    self._CreateMigrationFiles(fnames)
    self.assertListEqual(
        mysql_migration.ListMigrationsToProcess(self.temp_dir, None), fnames)

  def testReturnsOnlyMigrationsWithNumbersBiggerThanCurrentMigrationIndex(self):
    fnames = ["0000.sql", "0001.sql", "0002.sql", "0003.sql"]
    self._CreateMigrationFiles(fnames)
    self.assertListEqual(
        mysql_migration.ListMigrationsToProcess(self.temp_dir, 1),
        ["0002.sql", "0003.sql"])

  def testDoesNotAssumeLexicalSortingOrder(self):
    fnames = ["7.sql", "8.sql", "9.sql", "10.sql"]
    self._CreateMigrationFiles(fnames)
    self.assertListEqual(
        mysql_migration.ListMigrationsToProcess(self.temp_dir, None), fnames)


class MySQLMigrationTest(mysql_test.MySQLDatabaseProviderMixin,
                         absltest.TestCase):

  def _GetLatestMigrationNumber(self, conn):
    with contextlib.closing(conn.cursor()) as cursor:
      return mysql_migration.GetLatestMigrationNumber(cursor)

  def testMigrationsTableIsCorrectlyUpdates(self):
    all_migrations = mysql_migration.ListMigrationsToProcess(
        config.CONFIG["Mysql.migrations_dir"], None)
    self.assertEqual(
        self._conn._RunInTransaction(self._GetLatestMigrationNumber),
        len(all_migrations) - 1)

  def _DumpSchema(self, conn):
    with contextlib.closing(conn.cursor()) as cursor:
      return mysql_migration.DumpCurrentSchema(cursor)

  def testSavedSchemaIsUpToDate(self):
    # An up-to-date MySQL schema dump (formed by applying all the available
    # migrations) is stored in MySQL.schema_dump_path (currently - mysql.ddl).
    # This file has to be updated every time a new migration is introduced.
    # Please use test/grr_response_test/dump_mysql_schema.py to do that.
    schema = self._conn._RunInTransaction(self._DumpSchema)

    schema_dump_path = config.CONFIG["Mysql.schema_dump_path"]
    with io.open(schema_dump_path) as fd:
      saved_schema = fd.read()

    self.assertMultiLineEqual(
        schema.strip(),
        saved_schema.strip(),
        "%s is not updated. Make sure to run grr_dump_mysql_schema to update it"
        % os.path.basename(schema_dump_path))


if __name__ == "__main__":
  app.run(test_lib.main)
