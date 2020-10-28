#!/usr/bin/env python
# Lint as: python3
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from absl import app
from absl.testing import absltest

import mock

from grr_response_server.databases import db_clients_test
from grr_response_server.databases import db_test_utils
from grr_response_server.databases import mysql
from grr_response_server.databases import mysql_test
from grr_response_server.databases import mysql_utils
from grr_response_server.rdfvalues import objects as rdf_objects
from grr.test_lib import test_lib


class MysqlClientsTest(db_clients_test.DatabaseTestClientsMixin,
                       mysql_test.MysqlTestBase, absltest.TestCase):

  @mock.patch.object(mysql, "_SleepWithBackoff", lambda _: None)
  def testWriteClientSnapshot_duplicateKeyIsRetryable(self):
    with test_lib.FakeTime(1):
      client_id = db_test_utils.InitializeClient(self.db)
      snapshot = rdf_objects.ClientSnapshot(client_id=client_id)
      self.db.WriteClientSnapshot(snapshot)
      with self.assertRaises(mysql_utils.RetryableError):
        self.db.WriteClientSnapshot(snapshot)


if __name__ == "__main__":
  app.run(test_lib.main)
