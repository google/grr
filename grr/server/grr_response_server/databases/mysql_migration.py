#!/usr/bin/env python
"""Incremental MySQL migrations implementation."""
from __future__ import absolute_import
from __future__ import division

from __future__ import unicode_literals

import contextlib
import logging
import os
import time

from future.builtins import int

from MySQLdb.connections import Connection
from MySQLdb.cursors import Cursor

from typing import Callable, Optional, Sequence, Text


def GetLatestMigrationNumber(cursor):
  """Returns the number of the latest migration done."""
  cursor.execute("SELECT MAX(migration_id) FROM _migrations")
  rows = cursor.fetchall()
  return rows[0][0]


def _MigrationFilenameToInt(fname):
  """Converts migration filename to a migration number."""
  base, _ = os.path.splitext(fname)
  return int(base)


def ListMigrationsToProcess(migrations_root,
                            current_migration_number
                           ):
  """Lists filenames of migrations with numbers bigger than a given one."""
  migrations = []
  for m in os.listdir(migrations_root):
    if (current_migration_number is None or
        _MigrationFilenameToInt(m) > current_migration_number):
      migrations.append(m)

  return sorted(migrations, key=_MigrationFilenameToInt)


def ProcessMigrations(open_conn_fn,
                      migrations_root):
  """Processes migrations from a given folder.

  This function uses LOCK TABLE MySQL command on _migrations
  table to ensure that only one GRR process is actually
  performing the migration.

  We have to use open_conn_fn to open 2 connections to the database,
  since LOCK TABLE command is per-connection and it's not allowed
  to modify non-locked tables if LOCK TABLE was called within a
  connection. To overcome this limitation we use one connection
  to lock _migrations and perform its updates and one connection
  to do actual migrations.

  Args:
    open_conn_fn: A function to open new database connection.
    migrations_root: A path to folder with migration files.
  """
  with contextlib.closing(open_conn_fn()) as conn:
    conn.autocommit(True)

    with contextlib.closing(conn.cursor()) as cursor:
      cursor.execute("""CREATE TABLE IF NOT EXISTS _migrations(
        migration_id INT UNSIGNED PRIMARY KEY,
        timestamp TIMESTAMP(6) NOT NULL DEFAULT NOW(6)
        )""")

    with contextlib.closing(conn.cursor()) as cursor:
      cursor.execute('SELECT GET_LOCK("grr_migration", 3600)')

    try:
      with contextlib.closing(conn.cursor()) as cursor:
        current_migration = GetLatestMigrationNumber(cursor)

      to_process = ListMigrationsToProcess(migrations_root, current_migration)
      logging.info("Will execute following DB migrations: %s",
                   ", ".join(to_process))

      for fname in to_process:
        start_time = time.time()
        logging.info("Starting migration %s", fname)

        with open(os.path.join(migrations_root, fname)) as fd:
          sql = fd.read()
          with contextlib.closing(conn.cursor()) as cursor:
            cursor.execute(sql)

        logging.info("Migration %s is done. Took %.2fs", fname,
                     time.time() - start_time)

        # Update _migrations table with the latest migration.
        with contextlib.closing(conn.cursor()) as cursor:
          cursor.execute("INSERT INTO _migrations (migration_id) VALUES (%s)",
                         [_MigrationFilenameToInt(fname)])
    finally:
      with contextlib.closing(conn.cursor()) as cursor:
        cursor.execute('SELECT RELEASE_LOCK("grr_migration")')


def DumpCurrentSchema(cursor):
  """Dumps current database schema."""
  cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES "
                 "WHERE table_schema = (SELECT DATABASE())")
  defs = []
  for table, in sorted(cursor.fetchall()):
    cursor.execute("SHOW CREATE TABLE `{}`".format(table))
    rows = cursor.fetchall()
    defs.append(rows[0][1])

  return "\n\n".join(defs)
