#!/usr/bin/env python
import logging
import os
import random
import string

import MySQLdb

import unittest
from grr.server.databases import mysql

pytestmark = pytest.mark.skipif(
    not os.environ.get('MYSQL_TEST_USER'),
    'MYSQL_* environment variables not set')


class TestMysqlDB(unittest.TestCase):
  # TODO(user): Include DatabaseTestMixin (in db_test.py) once the
  # implementation is complete.

  def CreateDatabase(self):
    # pylint: disable=unreachable
    user = os.environ.get('MYSQL_TEST_USER')
    host = os.environ.get('MYSQL_TEST_HOST')
    port = os.environ.get('MYSQL_TEST_PORT')
    passwd = os.environ.get('MYSQL_TEST_PASS')
    dbname = ''.join(
        random.choice(string.ascii_uppercase + string.digits)
        for _ in range(10))

    connection = MySQLdb.Connect(host=host, port=port, user=user, passwd=passwd)
    cursor = connection.cursor()
    cursor.execute('CREATE DATABASE ' + dbname)
    logging.info('Created test database: %s', dbname)

    def Fin():
      cursor.execute('DROP DATABASE ' + dbname)
      cursor.close()
      connection.close()

    return mysql.MysqlDB(
        host=host, port=port, user=user, passwd=passwd, db=dbname), Fin
    # pylint: enable=unreachable

  def testCreate(self):
    _, fin = self.CreateDatabase()
    fin()


if __name__ == '__main__':
  unittest.main()
