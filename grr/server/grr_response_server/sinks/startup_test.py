#!/usr/bin/env python
from absl.testing import absltest
from grr_response_server.databases import db as abstract_db
from grr_response_server.databases import db_test_utils
from grr_response_server.sinks import startup as startup_sink
from grr.test_lib import db_test_lib
from grr_response_proto import rrg_pb2
from grr_response_proto.rrg import startup_pb2 as rrg_startup_pb2


class StartupSinkTest(absltest.TestCase):

  @db_test_lib.WithDatabase
  def testAccept(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeClient(db)

    startup = rrg_startup_pb2.Startup()
    startup.metadata.name = "RRG"

    parcel = rrg_pb2.Parcel()
    parcel.payload.Pack(startup)

    sink = startup_sink.StartupSink()
    sink.Accept(client_id, parcel)

    info = db.ReadClientFullInfo(client_id)
    self.assertEqual(info.last_rrg_startup.metadata.name, "RRG")


if __name__ == "__main__":
  absltest.main()
