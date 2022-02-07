#!/usr/bin/env python
from absl.testing import absltest

from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_server import flow_base
from grr_response_server.databases import db as abstract_db
from grr_response_server.databases import db_test_utils
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr.test_lib import db_test_lib


class FlowBaseTest(absltest.TestCase):

  class Flow(flow_base.FlowBase):
    pass

  _FLOW_ID = "FEDCBA9876543210"

  @db_test_lib.WithDatabase
  def testLogWithFormatArgs(self, db: abstract_db.Database) -> None:
    client_id = db_test_utils.InitializeClient(db)

    flow = rdf_flow_objects.Flow()
    flow.client_id = client_id
    flow.flow_id = self._FLOW_ID
    db.WriteFlowObject(flow)

    flow = FlowBaseTest.Flow(flow)
    flow.Log("foo %s %s", "bar", 42)

    logs = db.ReadFlowLogEntries(client_id, self._FLOW_ID, offset=0, count=1024)
    self.assertLen(logs, 1)
    self.assertEqual(logs[0].message, "foo bar 42")

  @db_test_lib.WithDatabase
  def testLogWithoutFormatArgs(self, db: abstract_db.Database) -> None:
    client_id = db_test_utils.InitializeClient(db)

    flow = rdf_flow_objects.Flow()
    flow.client_id = client_id
    flow.flow_id = self._FLOW_ID
    db.WriteFlowObject(flow)

    flow = FlowBaseTest.Flow(flow)
    flow.Log("foo %s %s")

    logs = db.ReadFlowLogEntries(client_id, self._FLOW_ID, offset=0, count=1024)
    self.assertLen(logs, 1)
    self.assertEqual(logs[0].message, "foo %s %s")

  @db_test_lib.WithDatabase
  def testClientInfo(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeClient(db)

    startup_info = rdf_client.StartupInfo()
    startup_info.client_info.client_name = "rrg"
    startup_info.client_info.client_version = 1337
    db.WriteClientStartupInfo(client_id, startup_info)

    flow = rdf_flow_objects.Flow()
    flow.client_id = client_id
    flow.flow_id = self._FLOW_ID

    flow = FlowBaseTest.Flow(flow)
    self.assertIsInstance(flow.client_info, rdf_client.ClientInformation)
    self.assertEqual(flow.client_info.client_name, "rrg")
    self.assertEqual(flow.client_info.client_version, 1337)

  @db_test_lib.WithDatabase
  def testClientInfoDefault(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeClient(db)

    flow = rdf_flow_objects.Flow()
    flow.client_id = client_id
    flow.flow_id = self._FLOW_ID

    flow = FlowBaseTest.Flow(flow)
    self.assertIsInstance(flow.client_info, rdf_client.ClientInformation)
    self.assertEmpty(flow.client_info.client_name)

  @db_test_lib.WithDatabase
  def testReturnsDefaultFlowProgressForEmptyFlow(self,
                                                 db: abstract_db.Database):
    client_id = db_test_utils.InitializeClient(db)

    flow = rdf_flow_objects.Flow()
    flow.client_id = client_id
    flow.flow_id = self._FLOW_ID
    db.WriteFlowObject(flow)

    flow_obj = FlowBaseTest.Flow(flow)
    progress = flow_obj.GetProgress()
    self.assertIsInstance(progress, rdf_flow_objects.DefaultFlowProgress)

  @db_test_lib.WithDatabase
  def testReturnsEmptyResultMetadataForEmptyFlow(self,
                                                 db: abstract_db.Database):
    client_id = db_test_utils.InitializeClient(db)

    flow = rdf_flow_objects.Flow()
    flow.client_id = client_id
    flow.flow_id = self._FLOW_ID
    db.WriteFlowObject(flow)

    flow_obj = FlowBaseTest.Flow(flow)
    result_metadata = flow_obj.GetResultMetadata()

    self.assertIsInstance(result_metadata, rdf_flow_objects.FlowResultMetadata)
    self.assertFalse(result_metadata.is_metadata_set)
    self.assertEmpty(result_metadata.num_results_per_type_tag)

  @db_test_lib.WithDatabase
  def testReturnsEmptyResultMetadataWithFlagSetForPersistedEmptyFlow(
      self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeClient(db)

    flow = rdf_flow_objects.Flow()
    flow.client_id = client_id
    flow.flow_id = self._FLOW_ID
    db.WriteFlowObject(flow)

    flow_obj = FlowBaseTest.Flow(flow)
    flow_obj.PersistState()
    result_metadata = flow_obj.GetResultMetadata()

    self.assertIsInstance(result_metadata, rdf_flow_objects.FlowResultMetadata)
    self.assertTrue(result_metadata.is_metadata_set)
    self.assertEmpty(result_metadata.num_results_per_type_tag)

  @db_test_lib.WithDatabase
  def testResultMetadataHasGroupedNumberOfReplies(self,
                                                  db: abstract_db.Database):
    client_id = db_test_utils.InitializeClient(db)

    flow = rdf_flow_objects.Flow()
    flow.client_id = client_id
    flow.flow_id = self._FLOW_ID
    db.WriteFlowObject(flow)

    flow_obj = FlowBaseTest.Flow(flow)
    flow_obj.SendReply(rdf_client.ClientInformation())
    flow_obj.SendReply(rdf_client.StartupInfo())
    flow_obj.SendReply(rdf_client.StartupInfo())
    flow_obj.SendReply(rdf_client.StartupInfo(), tag="foo")
    flow_obj.PersistState()
    db.WriteFlowObject(flow_obj.rdf_flow)

    flow_2 = db.ReadFlowObject(client_id, self._FLOW_ID)
    flow_obj_2 = FlowBaseTest.Flow(flow_2)

    result_metadata = flow_obj_2.GetResultMetadata()
    self.assertTrue(result_metadata.is_metadata_set)
    self.assertLen(result_metadata.num_results_per_type_tag, 3)

    sorted_counts = sorted(
        result_metadata.num_results_per_type_tag, key=lambda v: (v.type, v.tag))
    self.assertEqual(sorted_counts[0].type, "ClientInformation")
    self.assertEqual(sorted_counts[0].tag, "")
    self.assertEqual(sorted_counts[0].count, 1)
    self.assertEqual(sorted_counts[1].type, "StartupInfo")
    self.assertEqual(sorted_counts[1].tag, "")
    self.assertEqual(sorted_counts[1].count, 2)
    self.assertEqual(sorted_counts[2].type, "StartupInfo")
    self.assertEqual(sorted_counts[2].tag, "foo")
    self.assertEqual(sorted_counts[2].count, 1)

  @db_test_lib.WithDatabase
  def testResultMetadataAreCorrectlyUpdatedAfterMultiplePersistStateCalls(
      self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeClient(db)

    flow = rdf_flow_objects.Flow()
    flow.client_id = client_id
    flow.flow_id = self._FLOW_ID
    db.WriteFlowObject(flow)

    flow_obj = FlowBaseTest.Flow(flow)
    flow_obj.SendReply(rdf_client.ClientInformation())
    flow_obj.PersistState()
    flow_obj.PersistState()
    db.WriteFlowObject(flow_obj.rdf_flow)

    flow_2 = db.ReadFlowObject(client_id, self._FLOW_ID)
    flow_obj_2 = FlowBaseTest.Flow(flow_2)
    result_metadata = flow_obj_2.GetResultMetadata()

    self.assertLen(result_metadata.num_results_per_type_tag, 1)
    self.assertTrue(result_metadata.is_metadata_set)
    self.assertEqual(result_metadata.num_results_per_type_tag[0].type,
                     "ClientInformation")
    self.assertEqual(result_metadata.num_results_per_type_tag[0].tag, "")
    self.assertEqual(result_metadata.num_results_per_type_tag[0].count, 1)


if __name__ == "__main__":
  absltest.main()
