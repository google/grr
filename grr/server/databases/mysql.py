#!/usr/bin/env python
"""Mysql implementation of the GRR relational database abstraction.

See grr/server/db.py for interface.

"""
import logging
import MySQLdb

from grr.server.databases import mysql_ddl
from grr.server.databases import mysql_pool


class MysqlDB(object):
  """Implements db.Database using mysql.
  """

  # TODO(user): Inherit from Database (in server/db.py) once the
  # implementation is complete.

  def __init__(self, host=None, port=None, user=None, passwd=None, db=None):
    """Creates a datastore implementation.

    Args:
      host: Passed to MySQLdb.Connect when creating a new connection.
      port: Passed to MySQLdb.Connect when creating a new connection.
      user: Passed to MySQLdb.Connect when creating a new connection.
      passwd: Passed to MySQLdb.Connect when creating a new connection.
      db: Passed to MySQLdb.Connect when creating a new connection.
    """

    def Connect():
      return MySQLdb.Connect(
          host=host, port=port, user=user, passwd=passwd, db=db)

    self.pool = mysql_pool.Pool(Connect)
    self._InitializeSchema()

  def _InitializeSchema(self):
    """Initialize the database's schema."""
    connection = self.pool.get()
    cursor = connection.cursor()
    for command in mysql_ddl.SCHEMA_SETUP:
      try:
        cursor.execute(command)
      except Exception:
        logging.error("Failed to execute DDL: %s", command)
        raise
    cursor.close()
    connection.close()
