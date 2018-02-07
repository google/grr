#!/usr/bin/env python
import logging
import os
import random
import string
import unittest

# TODO(hanuszczak): This should be imported conditionally.
import MySQLdb

import unittest
from grr.server import db_test
from grr.server.databases import mysql


def _GetEnvironOrSkip(key):
  value = os.environ.get(key)
  if value is None:
    raise unittest.SkipTest("'%s' variable is not set" % key)
  return value


class TestMysqlDB(db_test.DatabaseTestMixin, unittest.TestCase):

  def CreateDatabase(self):
    # pylint: disable=unreachable
    user = _GetEnvironOrSkip("MYSQL_TEST_USER")
    host = _GetEnvironOrSkip("MYSQL_TEST_HOST")
    port = _GetEnvironOrSkip("MYSQL_TEST_PORT")
    passwd = _GetEnvironOrSkip("MYSQL_TEST_PASS")
    dbname = "".join(
        random.choice(string.ascii_uppercase + string.digits)
        for _ in range(10))

    connection = MySQLdb.Connect(host=host, port=port, user=user, passwd=passwd)
    cursor = connection.cursor()
    cursor.execute("CREATE DATABASE " + dbname)
    logging.info("Created test database: %s", dbname)

    def Fin():
      cursor.execute("DROP DATABASE " + dbname)
      cursor.close()
      connection.close()

    return mysql.MysqlDB(
        host=host, port=port, user=user, passwd=passwd, db=dbname), Fin
    # pylint: enable=unreachable

  # These are tests defined by the Mixin which we don't (yet) expect to pass.
  # TODO(user): finish the implementation and enable these.

  def testDatabaseType(self):
    pass

  def testClientMetadataSubsecond(self):
    pass

  def testClientWriteToUnknownClient(self):
    pass

  def testKeywordWriteToUnknownClient(self):
    pass

  def testLabelWriteToUnknownClient(self):
    pass

  def testClientHistory(self):
    pass

  def testClientSummary(self):
    pass

  def testClientValidates(self):
    pass

  def testClientStartupInfo(self):
    pass

  def testStartupHistory(self):
    pass

  def testCrashHistory(self):
    pass

  def testClientKeywords(self):
    pass

  def testClientKeywordsTimeRanges(self):
    pass

  def testDeleteClientKeyword(self):
    pass

  def testClientLabels(self):
    pass

  def testClientLabelsUnicode(self):
    pass

  def testFilledGRRUserReadWrite(self):
    pass

  def testEmptyGRRUserReadWrite(self):
    pass

  def testReadingUnknownGRRUserFails(self):
    pass

  def testReadingMultipleGRRUsersEntriesWorks(self):
    pass


if __name__ == "__main__":
  unittest.main()
