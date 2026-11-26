#!/usr/bin/env python
"""Tests for the MySQL migrations logic."""

from __future__ import annotations

from collections.abc import Sequence
import contextlib
import io
import os
import shutil

from absl import app
from absl.testing import absltest
import MySQLdb.connections

from grr_response_core import config
from grr_response_core.lib.util import temp
from grr_response_server.databases import mysql_migration
from grr_response_server.databases import mysql_pool
from grr_response_server.databases import mysql_test
from grr.test_lib import test_lib


class ListMigrationsToProcessTest(absltest.TestCase):

  def setUp(self):
    super().setUp()
    self.temp_dir = temp.TempDirPath()
    self.addCleanup(lambda: shutil.rmtree(self.temp_dir, ignore_errors=True))

  def _CreateMigrationFiles(self, fnames: Sequence[str]) -> None:
    for fname in fnames:
      with open(os.path.join(self.temp_dir, fname), "w"):
        pass

  def testReturnsAllMigrationsWhenCurrentNumberIsNone(self):
    fnames = ["0000.sql", "0001.sql", "0002.sql"]
    self._CreateMigrationFiles(fnames)
    self.assertListEqual(
        mysql_migration.ListMigrationsToProcess(self.temp_dir, None), fnames
    )

  def testReturnsOnlyMigrationsWithNumbersBiggerThanCurrentMigrationIndex(self):
    fnames = ["0000.sql", "0001.sql", "0002.sql", "0003.sql"]
    self._CreateMigrationFiles(fnames)
    self.assertListEqual(
        mysql_migration.ListMigrationsToProcess(self.temp_dir, 1),
        ["0002.sql", "0003.sql"],
    )

  def testDoesNotAssumeLexicalSortingOrder(self):
    fnames = ["7.sql", "8.sql", "9.sql", "10.sql"]
    self._CreateMigrationFiles(fnames)
    self.assertListEqual(
        mysql_migration.ListMigrationsToProcess(self.temp_dir, None), fnames
    )


class MySQLMigrationTest(
    mysql_test.MySQLDatabaseProviderMixin, absltest.TestCase
):

  def _GetLatestMigrationNumber(
      self,
      conn: MySQLdb.connections.Connection | mysql_pool._ConnectionProxy,
  ) -> int:
    with contextlib.closing(conn.cursor()) as cursor:
      return mysql_migration.GetLatestMigrationNumber(cursor)

  def testMigrationsTableIsCorrectlyUpdates(self):
    all_migrations = mysql_migration.ListMigrationsToProcess(
        config.CONFIG["Mysql.migrations_dir"], None
    )
    self.assertEqual(
        self._conn._RunInTransaction(self._GetLatestMigrationNumber),
        len(all_migrations) - 1,
    )

  def _DumpSchema(
      self,
      conn: MySQLdb.connections.Connection | mysql_pool._ConnectionProxy,
  ) -> str:
    with contextlib.closing(conn.cursor()) as cursor:
      return mysql_migration.DumpCurrentSchema(cursor)


if __name__ == "__main__":
  app.run(test_lib.main)
