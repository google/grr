#!/usr/bin/env python
"""Tests the fake data store - in memory implementation."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import errno
import socket
import threading
import time

from absl import app
from future.builtins import range
import portpicker

from grr_response_server import blob_store_test_mixin
from grr_response_server.databases import db_artifacts_test
from grr_response_server.databases import db_blob_references_test
from grr_response_server.databases import db_client_reports_test
from grr_response_server.databases import db_clients_test
from grr_response_server.databases import db_cronjob_test
from grr_response_server.databases import db_events_test
from grr_response_server.databases import db_flows_test
from grr_response_server.databases import db_foreman_rules_test
from grr_response_server.databases import db_hunts_test
from grr_response_server.databases import db_message_handler_test
from grr_response_server.databases import db_paths_test
from grr_response_server.databases import db_signed_binaries_test
from grr_response_server.databases import db_test_mixin
from grr_response_server.databases import db_test_utils
from grr_response_server.databases import db_users_test
from grr_response_test.lib import shared_mem_db
from grr.test_lib import test_lib


def _SetupServer():
  for _ in range(5):
    try:
      port = portpicker.pick_unused_port()
      server = shared_mem_db.SharedMemoryDBServer(port)
      return server
    except socket.error as e:
      if e.errno != errno.EADDRINUSE:
        raise

  raise RuntimeError("Unable to find an unused port after 5 tries.")


def _CreateServer():
  server = _SetupServer()

  server_thread = threading.Thread(
      name="SharedMemDBTestThread", target=server.serve_forever)
  server_thread.start()

  config_overrider = test_lib.ConfigOverrider(
      {"SharedMemoryDB.port": server.port})
  config_overrider.Start()

  # Give the server thread a chance to start up. If we don't sleep for at
  # least a tiny amount here, the server thread might not be able to get to
  # run at all before we send the first request.
  time.sleep(0.01)

  def TearDown():
    config_overrider.Stop()
    server.shutdown()
    server_thread.join()

  return server, TearDown


class SharedMemoryDBTest(
    db_artifacts_test.DatabaseTestArtifactsMixin,
    db_blob_references_test.DatabaseTestBlobReferencesMixin,
    db_client_reports_test.DatabaseTestClientReportsMixin,
    db_clients_test.DatabaseTestClientsMixin,
    db_cronjob_test.DatabaseTestCronJobMixin,
    db_events_test.DatabaseTestEventsMixin,
    db_flows_test.DatabaseTestFlowMixin,
    db_foreman_rules_test.DatabaseTestForemanRulesMixin,
    db_hunts_test.DatabaseTestHuntMixin,
    db_message_handler_test.DatabaseTestHandlerMixin,
    db_paths_test.DatabaseTestPathsMixin,
    db_signed_binaries_test.DatabaseTestSignedBinariesMixin,
    db_users_test.DatabaseTestUsersMixin,
    # Special mixin for easier testing of list/query methods.
    db_test_utils.QueryTestHelpersMixin,
    blob_store_test_mixin.BlobStoreTestMixin,
    db_test_mixin.DatabaseSetupMixin,
    test_lib.GRRBaseTest):
  """Test the shared memory db."""

  @classmethod
  def setUpClass(cls):
    super(SharedMemoryDBTest, cls).setUpClass()
    cls.server_tear_down_pair = _CreateServer()

  @classmethod
  def tearDownClass(cls):
    _, tear_down_fn = cls.server_tear_down_pair
    tear_down_fn()
    super(SharedMemoryDBTest, cls).tearDownClass()

  def CreateDatabase(self):
    server, _ = self.__class__.server_tear_down_pair
    server.Reset()

    created_db = shared_mem_db.SharedMemoryDB()

    def TearDown():
      created_db.UnregisterFlowProcessingHandler()
      created_db.UnregisterMessageHandler()

    return created_db, TearDown

  def CreateBlobStore(self):
    return self.CreateDatabase()

  # No need to load-test test-only DB.
  def test40000ResponsesCanBeWrittenAndRead(self):
    pass

  # No need to load-test test-only DB.
  def testWritesAndCounts40001FlowResults(self):
    pass

  # No need to load-test test-only DB.
  def testDeleteAllFlowRequestsAndResponsesHandles11000Responses(self):
    pass

  # No need to load-test test-only DB.
  def testDeleteFlowRequestsHandles11000Responses(self):
    pass

  # TODO(user): UpdateHuntOutputState accepts lambda as an argument
  # (which is not pickleable). Refactor the API so that it doesn't
  # require a callback.
  def testUpdatingHuntOutputStateForUnknownHuntRaises(self):
    pass

  # TODO(user): UpdateHuntOutputState accepts lambda as an argument
  # (which is not pickleable). Refactor the API so that it doesn't
  # require a callback.
  def testUpdatingHuntOutputStateWorksCorrectly(self):
    pass

  # TODO(user): UpdateHuntOutputState accepts lambda as an argument
  # (which is not pickleable). Refactor the API so that it doesn't
  # require a callback.
  def testWritingAndReadingHuntOutputPluginsStatesWorks(self):
    pass


def main(args):
  test_lib.main(args)


if __name__ == "__main__":
  app.run(main)
