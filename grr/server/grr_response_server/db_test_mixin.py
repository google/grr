#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""Mixin class to be used in tests for DB implementations."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import abc
from future.utils import with_metaclass
import mock

from grr_response_server import data_store
from grr_response_server import db
from grr_response_server import db_artifacts_test
from grr_response_server import db_blob_references_test
from grr_response_server import db_client_reports_test
from grr_response_server import db_clients_test
from grr_response_server import db_cronjob_test
from grr_response_server import db_events_test
from grr_response_server import db_foreman_rules_test
from grr_response_server import db_hunts_test
from grr_response_server import db_message_handler_test
from grr_response_server import db_paths_test
from grr_response_server import db_signed_binaries_test
from grr_response_server import db_test_utils
from grr_response_server import db_users_test


class DatabaseProvider(with_metaclass(abc.ABCMeta, object)):
  """An abstract class that provides tests with a database."""

  @abc.abstractmethod
  def CreateDatabase(self):
    """Create a test database.

    Returns:
      A pair (db, cleanup), where db is an instance of db.Database to be tested
      and cleanup is a function which destroys db, releasing any resources held
      by it.
    """


class DatabaseSetupMixin(DatabaseProvider):
  """A mixin that adds a setup method to tests that instantiates self.db."""

  def setUp(self):
    # Set up database before calling super.setUp(), in case any other mixin
    # depends on db during its setup.
    db_obj, cleanup = self.CreateDatabase()
    self.db = db.DatabaseValidationWrapper(db_obj)

    if cleanup:
      self.addCleanup(cleanup)

    # In case a test registers a message handler, unregister it.
    self.addCleanup(self.db.UnregisterMessageHandler)

    super(DatabaseSetupMixin, self).setUp()


class DatabaseTestMixin(
    with_metaclass(
        abc.ABCMeta,
        DatabaseSetupMixin,
        db_artifacts_test.DatabaseTestArtifactsMixin,
        db_blob_references_test.DatabaseBlobReferencesTestMixin,
        db_client_reports_test.DatabaseTestClientReportsMixin,
        db_clients_test.DatabaseTestClientsMixin,
        db_cronjob_test.DatabaseTestCronJobMixin,
        db_events_test.DatabaseEventsTestMixin,
        db_foreman_rules_test.DatabaseTestForemanRulesMixin,
        db_hunts_test.DatabaseTestHuntMixin,
        db_message_handler_test.DatabaseTestHandlerMixin,
        db_paths_test.DatabaseTestPathsMixin,
        db_signed_binaries_test.DatabaseTestSignedBinariesMixin,
        db_users_test.DatabaseTestUsersMixin,
        # Special mixin for easier testing of list/query methods.
        db_test_utils.QueryTestHelpersMixin)):
  """An abstract class for testing db.Database implementations.

  Implementations should override CreateDatabase in order to produce
  a test suite for a particular implementation of db.Database.

  This class does not inherit from `TestCase` to prevent the test runner from
  executing its method. Instead it should be mixed into the actual test classes.
  """

  def testDatabaseType(self):
    d = self.db
    self.assertIsInstance(d, db.Database)

  def testDatabaseHandlesUnicodeCorrectly(self):
    name = "🍻foo🍻"
    self.db.WriteGRRUser(name)
    user = self.db.ReadGRRUser(name)
    self.assertLen(user.username, 5)
    self.assertEqual(user.username, name)


class GlobalDatabaseTestMixin(DatabaseProvider):
  """Mixin that sets `data_store.REL_DB` to the test database.

  The test database is provided by self.CreateDatabase(), which in turn is
  provided by another Mixin, e.g. MySQL.
  """

  def setUp(self):
    # Set up database before calling super.setUp(), in case any other mixin
    # depends on db during its setup.
    db_obj, cleanup = self.CreateDatabase()
    patcher = mock.patch.object(data_store, "REL_DB",
                                db.DatabaseValidationWrapper(db_obj))
    patcher.start()
    self.addCleanup(patcher.stop)

    if cleanup:
      self.addCleanup(cleanup)

    # In case a test registers a message handler, unregister it.
    self.addCleanup(data_store.REL_DB.UnregisterMessageHandler)

    super(GlobalDatabaseTestMixin, self).setUp()
