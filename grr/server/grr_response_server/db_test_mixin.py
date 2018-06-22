#!/usr/bin/env python
"""Mixin class to be used in tests for DB implementations."""

import abc
import random

from grr.server.grr_response_server import db
from grr.server.grr_response_server import db_clients_test
from grr.server.grr_response_server import db_cronjob_test
from grr.server.grr_response_server import db_events_test
from grr.server.grr_response_server import db_foreman_rules_test
from grr.server.grr_response_server import db_message_handler_test
from grr.server.grr_response_server import db_paths_test
from grr.server.grr_response_server import db_users_test


class DatabaseTestMixin(
    db_clients_test.DatabaseTestClientsMixin,
    db_cronjob_test.DatabaseTestCronjobMixin,
    db_events_test.DatabaseEventsTestMixin,
    db_foreman_rules_test.DatabaseTestForemanRulesMixin,
    db_message_handler_test.DatabaseTestHandlerMixin,
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
    super(DatabaseTestMixin, self).setUp()
    db_obj, self.cleanup = self.CreateDatabase()
    self.db = db.DatabaseValidationWrapper(db_obj)

  def tearDown(self):
    if self.cleanup:
      self.cleanup()
    super(DatabaseTestMixin, self).tearDown()

  def testDatabaseType(self):
    d = self.db
    self.assertIsInstance(d, db.Database)

  def InitializeClient(self, client_id=None):
    """Initializes a test client.

    Args:
      client_id: A specific client id to use for initialized client. If none is
                 provided a randomly generated one is used.

    Returns:
      A client id for initialized client.
    """
    if client_id is None:
      client_id = "C."
      for _ in range(16):
        client_id += random.choice("0123456789abcdef")

    self.db.WriteClientMetadata(client_id, fleetspeak_enabled=True)
    return client_id
