#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
import abc

from grr.server import db
from grr.server import db_clients_test
from grr.server import db_paths_test
from grr.server import db_users_test


class DatabaseTestMixin(
    db_clients_test.DatabaseTestClientsMixin,
    db_paths_test.DatabaseTestPathsMixin,
    db_users_test.DatabaseTestUsersMixin,
):
  """An abstract class for testing db.Database implementations.

  Implementations should override CreateDatabase in order to produce
  a test suite for a particular implementation of db.Database.

  This class does not inherit from `TestCase` to prevent the test runner from
  executing its method. Instead it should be mixed into the actual test classes.
  """
  __metaclass__ = abc.ABCMeta

  @abc.abstractmethod
  def CreateDatabase(self):
    """Create a test database.

    Returns:
      A pair (db, cleanup), where db is an instance of db.Database to be tested
      and cleanup is a function which destroys db, releasing any resources held
      by it.
    """

  def setUp(self):
    self.db, self.cleanup = self.CreateDatabase()

  def tearDown(self):
    if self.cleanup:
      self.cleanup()

  def testDatabaseType(self):
    d = self.db
    self.assertIsInstance(d, db.Database)
