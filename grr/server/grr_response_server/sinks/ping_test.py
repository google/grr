#!/usr/bin/env python
import time

from absl.testing import absltest

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.stats import default_stats_collector
from grr_response_core.stats import stats_collector_instance
from grr_response_server import hunt
from grr_response_server import worker_lib
from grr_response_server.databases import db as abstract_db
from grr_response_server.databases import db_test_utils
from grr_response_server.flows.general import memsize
from grr_response_server.sinks import ping as ping_sink
from grr.test_lib import db_test_lib
from grr_response_proto import rrg_pb2
from grr_response_proto.rrg import ping_pb2 as rrg_ping_pb2


class PingSinkTest(absltest.TestCase):

  @classmethod
  def setUpClass(cls):
    super().setUpClass()

    # TODO: Remove once the "default" instance is actually
    # default.
    stats_collector_instance.Set(
        default_stats_collector.DefaultStatsCollector()
    )

  @db_test_lib.WithDatabase
  def testAccept_HuntTrigger(self, db: abstract_db.Database):
    username = db_test_utils.InitializeUser(db)
    client_id = db_test_utils.InitializeRRGClient(db)

    db.RegisterMessageHandler(
        worker_lib.ProcessMessageHandlerRequests,
        lease_time=rdfvalue.Duration.From(10, rdfvalue.SECONDS),
    )
    self.addCleanup(db.UnregisterMessageHandler)

    hunt_id = hunt.CreateAndStartHunt(
        flow_name=memsize.GetMemorySize.__name__,
        flow_args=rdf_flows.EmptyFlowArgs(),
        creator=username,
    )

    ping = rrg_ping_pb2.Ping()
    ping.send_time.GetCurrentTime()
    ping.seq = 42

    ping_parcel = rrg_pb2.Parcel()
    ping_parcel.sink = rrg_pb2.Sink.PING
    ping_parcel.payload.Pack(ping)

    ping_sink.PingSink().Accept(client_id, ping_parcel)

    # Wait until message handler processes messages.
    while db.ReadMessageHandlerRequests():
      time.sleep(0)

    flow_objs = db.ReadAllFlowObjects(client_id)
    self.assertLen(flow_objs, 1)
    self.assertEqual(flow_objs[0].client_id, client_id)
    self.assertEqual(flow_objs[0].parent_hunt_id, hunt_id)


if __name__ == "__main__":
  absltest.main()
