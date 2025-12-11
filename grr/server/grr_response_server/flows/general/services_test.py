#!/usr/bin/env python
from collections.abc import Iterator

from absl.testing import absltest

from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import mig_client
from grr_response_proto import objects_pb2
from grr_response_proto import sysinfo_pb2
from grr_response_server import data_store
from grr_response_server.databases import db as abstract_db
from grr_response_server.databases import db_test_utils
from grr_response_server.flows.general import services
from grr.test_lib import action_mocks
from grr.test_lib import flow_test_lib
from grr.test_lib import testing_startup


class ListRunningServicesTest(flow_test_lib.FlowTestsBaseclass):

  @classmethod
  def setUpClass(cls):
    super().setUpClass()
    testing_startup.TestInit()

  def testMacos(self):
    assert data_store.REL_DB is not None
    db: abstract_db.Database = data_store.REL_DB

    creator = db_test_utils.InitializeUser(db)
    client_id = db_test_utils.InitializeClient(db)

    snapshot = objects_pb2.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.os = "Darwin"
    db.WriteClientSnapshot(snapshot)

    class ActionMock(action_mocks.ActionMock):

      def OSXEnumerateRunningServices(
          self,
          args: None,
      ) -> Iterator[rdf_client.OSXServiceInformation]:
        del args  # Unused.

        yield mig_client.ToRDFOSXServiceInformation(
            sysinfo_pb2.OSXServiceInformation(
                label="com.apple.netbiosd",
                program="/usr/sbin/netbiosd",
                pid=34567,
                sessiontype="System",
                ondemand=True,
            )
        )
        yield mig_client.ToRDFOSXServiceInformation(
            sysinfo_pb2.OSXServiceInformation(
                label="com.google.fleetspeak",
                program="/usr/sbin/fleetspeakd",
                sessiontype="System",
                pid=12345,
                ondemand=False,
            )
        )
        yield mig_client.ToRDFOSXServiceInformation(
            sysinfo_pb2.OSXServiceInformation(
                label="com.apple.syslogd",
                program="/usr/sbin/syslogd",
                sessiontype="System",
                pid=333,
                ondemand=False,
            )
        )

    flow_id = flow_test_lib.StartAndRunFlow(
        services.ListRunningServices,
        ActionMock(),
        client_id=client_id,
        creator=creator,
    )

    results = flow_test_lib.GetFlowResults(client_id, flow_id)
    self.assertLen(results, 3)

    self.assertEqual(results[0].label, "com.apple.netbiosd")
    self.assertEqual(results[0].program, "/usr/sbin/netbiosd")
    self.assertEqual(results[0].pid, 34567)
    self.assertEqual(results[0].sessiontype, "System")
    self.assertTrue(results[0].ondemand)

    self.assertEqual(results[1].label, "com.google.fleetspeak")
    self.assertEqual(results[1].program, "/usr/sbin/fleetspeakd")
    self.assertEqual(results[1].pid, 12345)
    self.assertEqual(results[1].sessiontype, "System")
    self.assertFalse(results[1].ondemand)

    self.assertEqual(results[2].label, "com.apple.syslogd")
    self.assertEqual(results[2].program, "/usr/sbin/syslogd")
    self.assertEqual(results[2].pid, 333)
    self.assertEqual(results[2].sessiontype, "System")
    self.assertFalse(results[2].ondemand)


if __name__ == "__main__":
  absltest.main()
