#!/usr/bin/env python
from absl.testing import absltest

from grr_response_proto import objects_pb2
from grr_response_server import data_store_utils
from grr_response_server.databases import db as abstract_db
from grr_response_server.databases import db_test_utils
from grr.test_lib import db_test_lib


class GetClientOsTest(absltest.TestCase):

  @db_test_lib.WithDatabase
  def testSnapshotNotAvailable(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeClient(db)

    self.assertEmpty(data_store_utils.GetClientOs(client_id))

  @db_test_lib.WithDatabase
  def testSnapshotAvailable(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeClient(db)

    snapshot = objects_pb2.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.os = "Windows"
    db.WriteClientSnapshot(snapshot)

    self.assertEqual(data_store_utils.GetClientOs(client_id), "Windows")


if __name__ == "__main__":
  absltest.main()
