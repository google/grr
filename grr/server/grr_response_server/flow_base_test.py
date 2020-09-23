#!/usr/bin/env python
from absl.testing import absltest

from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_server import flow_base
from grr_response_server.databases import db as abstract_db
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr.test_lib import db_test_lib


class FlowBaseTest(absltest.TestCase):

  class Flow(flow_base.FlowBase):
    pass

  @db_test_lib.WithDatabase
  def testClientInfo(self, db: abstract_db.Database):
    client_id = "C.0123456789ABCDEF"
    db.WriteClientMetadata(client_id, fleetspeak_enabled=False)

    startup_info = rdf_client.StartupInfo()
    startup_info.client_info.client_name = "rrg"
    startup_info.client_info.client_version = 1337
    db.WriteClientStartupInfo(client_id, startup_info)

    flow = rdf_flow_objects.Flow()
    flow.client_id = client_id
    flow.flow_id = "FEDCBA9876543210"

    flow = FlowBaseTest.Flow(flow)
    self.assertIsInstance(flow.client_info, rdf_client.ClientInformation)
    self.assertEqual(flow.client_info.client_name, "rrg")
    self.assertEqual(flow.client_info.client_version, 1337)

  @db_test_lib.WithDatabase
  def testClientInfoDefault(self, db: abstract_db.Database):
    client_id = "C.0123456789ABCDEF"
    db.WriteClientMetadata(client_id, fleetspeak_enabled=False)

    flow = rdf_flow_objects.Flow()
    flow.client_id = client_id
    flow.flow_id = "FEDCBA9876543210"

    flow = FlowBaseTest.Flow(flow)
    self.assertIsInstance(flow.client_info, rdf_client.ClientInformation)
    self.assertEmpty(flow.client_info.client_name)


if __name__ == "__main__":
  absltest.main()
