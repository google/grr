#!/usr/bin/env python
from unittest import mock

from absl.testing import absltest

from google.protobuf import any_pb2
from google.protobuf import empty_pb2
from google.protobuf import wrappers_pb2
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.stats import default_stats_collector
from grr_response_core.stats import metrics
from grr_response_core.stats import stats_collector_instance
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_proto import objects_pb2
from grr_response_proto import tests_pb2
from grr_response_server import action_registry
from grr_response_server import data_store
from grr_response_server import flow_base
from grr_response_server import flow_responses
from grr_response_server.databases import db as abstract_db
from grr_response_server.databases import db_test_utils
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr_response_server.rdfvalues import mig_flow_objects
from grr.test_lib import action_mocks
from grr.test_lib import db_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import rrg_test_lib
from grr.test_lib import stats_test_lib
from grr.test_lib import test_lib
from grr.test_lib import testing_startup
from grr_response_proto import rrg_pb2
from grr_response_proto.rrg import os_pb2 as rrg_os_pb2
from grr_response_proto.rrg import startup_pb2 as rrg_startup_pb2


class FlowBaseTest(
    flow_test_lib.FlowTestsBaseclass, stats_test_lib.StatsCollectorTestMixin
):

  @classmethod
  def setUpClass(cls):
    super(FlowBaseTest, cls).setUpClass()
    testing_startup.TestInit()

  class Flow(flow_base.FlowBase):
    pass

  _FLOW_ID = "FEDCBA9876543210"

  @db_test_lib.WithDatabase
  def testLogWithFormatArgs(self, db: abstract_db.Database) -> None:
    client_id = db_test_utils.InitializeClient(db)

    flow = rdf_flow_objects.Flow()
    flow.client_id = client_id
    flow.flow_id = self._FLOW_ID
    db.WriteFlowObject(mig_flow_objects.ToProtoFlow(flow))

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
    db.WriteFlowObject(mig_flow_objects.ToProtoFlow(flow))

    flow = FlowBaseTest.Flow(flow)
    flow.Log("foo %s %s")

    logs = db.ReadFlowLogEntries(client_id, self._FLOW_ID, offset=0, count=1024)
    self.assertLen(logs, 1)
    self.assertEqual(logs[0].message, "foo %s %s")

  @db_test_lib.WithDatabase
  def testClientInfo(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeClient(db)

    startup_info = jobs_pb2.StartupInfo()
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
  def testClientLabels(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeClient(db)
    user = db_test_utils.InitializeUser(db)

    db.AddClientLabels(client_id, owner=user, labels=["foo"])
    db.AddClientLabels(client_id, owner=user, labels=["bar"])

    flow = rdf_flow_objects.Flow()
    flow.client_id = client_id
    flow.flow_id = self._FLOW_ID

    flow = FlowBaseTest.Flow(flow)
    self.assertIn("foo", flow.client_labels)
    self.assertIn("bar", flow.client_labels)

  @db_test_lib.WithDatabase
  def testClientLabels_Empty(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeClient(db)

    flow = rdf_flow_objects.Flow()
    flow.client_id = client_id
    flow.flow_id = self._FLOW_ID

    flow = FlowBaseTest.Flow(flow)
    self.assertEmpty(flow.client_labels)

  @db_test_lib.WithDatabase
  def testPythonAgentSupportFalse(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(db)

    flow = rdf_flow_objects.Flow()
    flow.client_id = client_id
    flow.flow_id = self._FLOW_ID

    flow = FlowBaseTest.Flow(flow)
    self.assertFalse(flow.python_agent_support)

  @db_test_lib.WithDatabase
  def testPythonAgentSupportFalse_Empty(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(db)

    startup = jobs_pb2.StartupInfo()
    db.WriteClientStartupInfo(client_id, startup)

    flow = rdf_flow_objects.Flow()
    flow.client_id = client_id
    flow.flow_id = self._FLOW_ID

    flow = FlowBaseTest.Flow(flow)
    self.assertFalse(flow.python_agent_support)

  @db_test_lib.WithDatabase
  def testPythonAgentSupportTrue(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeClient(db)

    startup = jobs_pb2.StartupInfo()
    startup.client_info.client_version = 4321
    db.WriteClientStartupInfo(client_id, startup)

    flow = rdf_flow_objects.Flow()
    flow.client_id = client_id
    flow.flow_id = self._FLOW_ID

    flow = FlowBaseTest.Flow(flow)
    self.assertTrue(flow.python_agent_support)

  @db_test_lib.WithDatabase
  def testNoRrgStartup(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeClient(db)

    flow = rdf_flow_objects.Flow()
    flow.client_id = client_id
    flow.flow_id = self._FLOW_ID

    flow = FlowBaseTest.Flow(flow)
    self.assertEmpty(flow.rrg_startup.metadata.name)
    self.assertEqual(flow.rrg_startup.metadata.version.major, 0)
    self.assertEqual(flow.rrg_startup.metadata.version.minor, 0)
    self.assertEqual(flow.rrg_startup.metadata.version.patch, 0)
    self.assertEmpty(flow.rrg_startup.path.raw_bytes)

  @db_test_lib.WithDatabase
  def testRrgStartup(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeClient(db)

    rrg_startup = rrg_startup_pb2.Startup()
    rrg_startup.metadata.name = "RRG"
    rrg_startup.metadata.version.major = 1
    rrg_startup.metadata.version.minor = 2
    rrg_startup.metadata.version.patch = 3
    rrg_startup.path.raw_bytes = "/usr/sbin/rrg".encode()
    db.WriteClientRRGStartup(client_id, rrg_startup)

    flow = rdf_flow_objects.Flow()
    flow.client_id = client_id
    flow.flow_id = self._FLOW_ID

    flow = FlowBaseTest.Flow(flow)
    self.assertEqual(flow.rrg_startup.metadata.name, "RRG")
    self.assertEqual(flow.rrg_startup.metadata.version.major, 1)
    self.assertEqual(flow.rrg_startup.metadata.version.minor, 2)
    self.assertEqual(flow.rrg_startup.metadata.version.patch, 3)
    self.assertEqual(flow.rrg_startup.path.raw_bytes, "/usr/sbin/rrg".encode())

  @db_test_lib.WithDatabase
  def testNoRrgVersion(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeClient(db)

    flow = rdf_flow_objects.Flow()
    flow.client_id = client_id
    flow.flow_id = self._FLOW_ID

    flow = FlowBaseTest.Flow(flow)
    self.assertFalse(flow.rrg_support)
    self.assertEqual(flow.rrg_version, (0, 0, 0))

  @db_test_lib.WithDatabase
  def testRrgVersion(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(db)

    rrg_startup = rrg_startup_pb2.Startup()
    rrg_startup.metadata.version.major = 1
    rrg_startup.metadata.version.minor = 2
    rrg_startup.metadata.version.patch = 3
    db.WriteClientRRGStartup(client_id, rrg_startup)

    flow = rdf_flow_objects.Flow()
    flow.client_id = client_id
    flow.flow_id = self._FLOW_ID

    flow = FlowBaseTest.Flow(flow)
    self.assertEqual(flow.rrg_version, (1, 2, 3))

  @db_test_lib.WithDatabase
  def testRrgSupport(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(db)

    flow = rdf_flow_objects.Flow()
    flow.client_id = client_id
    flow.flow_id = self._FLOW_ID

    flow = FlowBaseTest.Flow(flow)
    self.assertTrue(flow.rrg_support, True)

  @db_test_lib.WithDatabase
  def testRrgSupport_Disable(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(db)

    flow = rdf_flow_objects.Flow()
    flow.client_id = client_id
    flow.flow_id = self._FLOW_ID
    flow.disable_rrg_support = True

    flow = FlowBaseTest.Flow(flow)
    self.assertFalse(flow.rrg_support)

  @db_test_lib.WithDatabase
  def testRrgOsType(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(db)

    startup = rrg_startup_pb2.Startup()
    startup.metadata.version.major = 0
    startup.metadata.version.minor = 0
    startup.metadata.version.patch = 4
    startup.os_type = rrg_os_pb2.LINUX
    db.WriteClientRRGStartup(client_id, startup)

    flow = rdf_flow_objects.Flow()
    flow.client_id = client_id
    flow.flow_id = self._FLOW_ID

    flow = FlowBaseTest.Flow(flow)
    self.assertEqual(flow.rrg_os_type, rrg_os_pb2.LINUX)

  @db_test_lib.WithDatabase
  def testRrgOsTypeFallback(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(db)

    startup = rrg_startup_pb2.Startup()
    startup.metadata.version.major = 0
    startup.metadata.version.minor = 0
    startup.metadata.version.patch = 1
    db.WriteClientRRGStartup(client_id, startup)

    snapshot = objects_pb2.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.os = "Linux"
    data_store.REL_DB.WriteClientSnapshot(snapshot)

    flow = rdf_flow_objects.Flow()
    flow.client_id = client_id
    flow.flow_id = self._FLOW_ID

    flow = FlowBaseTest.Flow(flow)
    self.assertEqual(flow.rrg_os_type, rrg_os_pb2.LINUX)

  @db_test_lib.WithDatabase
  def testDefaultExcludeLabels_Empty(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(db)

    flow = rdf_flow_objects.Flow()
    flow.client_id = client_id

    flow = FlowBaseTest.Flow(flow)
    self.assertEmpty(flow.default_exclude_labels)

  @db_test_lib.WithDatabase
  def testDefaultExcludeLabels(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeClient(db)

    with test_lib.ConfigOverrider(
        {"AdminUI.hunt_config": {"default_exclude_labels": ["foo", "bar"]}}
    ):
      flow = rdf_flow_objects.Flow()
      flow.client_id = client_id

      flow = FlowBaseTest.Flow(flow)
      self.assertIn("foo", flow.default_exclude_labels)
      self.assertIn("bar", flow.default_exclude_labels)

  @db_test_lib.WithDatabase
  def testClientHasExcludeLabels(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(db)
    user = db_test_utils.InitializeUser(db)

    db.AddClientLabels(client_id, owner=user, labels=["foo"])

    with test_lib.ConfigOverrider(
        {"AdminUI.hunt_config": {"default_exclude_labels": ["foo", "bar"]}}
    ):

      flow = rdf_flow_objects.Flow()
      flow.client_id = client_id

      flow = FlowBaseTest.Flow(flow)
      self.assertTrue(flow.client_has_exclude_labels)

  @db_test_lib.WithDatabase
  def testClientHasNoExcludeLabels(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(db)
    user = db_test_utils.InitializeUser(db)

    db.AddClientLabels(client_id, owner=user, labels=["baz"])

    with test_lib.ConfigOverrider(
        {"AdminUI.hunt_config": {"default_exclude_labels": ["foo", "bar"]}}
    ):
      flow = rdf_flow_objects.Flow()
      flow.client_id = client_id

      flow = FlowBaseTest.Flow(flow)
      self.assertFalse(flow.client_has_exclude_labels)

  @db_test_lib.WithDatabase
  def testReturnsDefaultFlowProgressForEmptyFlow(
      self, db: abstract_db.Database
  ):
    client_id = db_test_utils.InitializeClient(db)

    flow = rdf_flow_objects.Flow()
    flow.client_id = client_id
    flow.flow_id = self._FLOW_ID
    db.WriteFlowObject(mig_flow_objects.ToProtoFlow(flow))

    flow_obj = FlowBaseTest.Flow(flow)
    progress = flow_obj.GetProgress()
    self.assertIsInstance(progress, rdf_flow_objects.DefaultFlowProgress)

    progress = flow_obj.GetProgressProto()
    self.assertIsInstance(progress, flows_pb2.DefaultFlowProgress)

  @db_test_lib.WithDatabase
  def testReturnsEmptyResultMetadataForEmptyFlow(
      self, db: abstract_db.Database
  ):
    client_id = db_test_utils.InitializeClient(db)

    flow = rdf_flow_objects.Flow()
    flow.client_id = client_id
    flow.flow_id = self._FLOW_ID
    db.WriteFlowObject(mig_flow_objects.ToProtoFlow(flow))

    flow_2 = db.ReadFlowObject(client_id, self._FLOW_ID)
    result_metadata = flow_2.result_metadata

    self.assertIsInstance(result_metadata, flows_pb2.FlowResultMetadata)
    self.assertFalse(result_metadata.is_metadata_set)
    self.assertEmpty(result_metadata.num_results_per_type_tag)

  @db_test_lib.WithDatabase
  def testReturnsEmptyResultMetadataWithFlagSetForPersistedEmptyFlow(
      self, db: abstract_db.Database
  ):
    client_id = db_test_utils.InitializeClient(db)

    flow = rdf_flow_objects.Flow()
    flow.client_id = client_id
    flow.flow_id = self._FLOW_ID
    db.WriteFlowObject(mig_flow_objects.ToProtoFlow(flow))

    flow_obj = FlowBaseTest.Flow(flow)
    flow_obj.PersistState()

    db.WriteFlowObject(mig_flow_objects.ToProtoFlow(flow_obj.rdf_flow))
    flow_2 = db.ReadFlowObject(client_id, self._FLOW_ID)
    result_metadata = flow_2.result_metadata

    self.assertIsInstance(result_metadata, flows_pb2.FlowResultMetadata)
    self.assertTrue(result_metadata.is_metadata_set)
    self.assertEmpty(result_metadata.num_results_per_type_tag)

  @db_test_lib.WithDatabase
  def testResultMetadataHasGroupedNumberOfReplies(
      self, db: abstract_db.Database
  ):
    client_id = db_test_utils.InitializeClient(db)

    flow = rdf_flow_objects.Flow()
    flow.client_id = client_id
    flow.flow_id = self._FLOW_ID
    db.WriteFlowObject(mig_flow_objects.ToProtoFlow(flow))

    flow_obj = FlowBaseTest.Flow(flow)
    flow_obj.SendReply(rdf_client.ClientInformation())
    flow_obj.SendReply(rdf_client.StartupInfo())
    flow_obj.SendReply(rdf_client.StartupInfo())
    flow_obj.SendReply(rdf_client.StartupInfo(), tag="foo")
    flow_obj.PersistState()
    db.WriteFlowObject(mig_flow_objects.ToProtoFlow(flow_obj.rdf_flow))

    flow_2 = db.ReadFlowObject(client_id, self._FLOW_ID)
    result_metadata = flow_2.result_metadata

    self.assertIsInstance(result_metadata, flows_pb2.FlowResultMetadata)
    self.assertTrue(result_metadata.is_metadata_set)
    self.assertLen(result_metadata.num_results_per_type_tag, 3)

    sorted_counts = sorted(
        result_metadata.num_results_per_type_tag, key=lambda v: (v.type, v.tag)
    )
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
  def testResultMetadataHasGroupedNumberOfRepliesProto(
      self, db: abstract_db.Database
  ):
    client_id = db_test_utils.InitializeClient(db)

    class MultipleReturnTypesSendReplyProto(flow_base.FlowBase):
      proto_result_types = [jobs_pb2.ClientInformation, jobs_pb2.StartupInfo]

    flow = rdf_flow_objects.Flow()
    flow.client_id = client_id
    flow.flow_id = self._FLOW_ID
    db.WriteFlowObject(mig_flow_objects.ToProtoFlow(flow))

    flow_obj = MultipleReturnTypesSendReplyProto(flow)
    flow_obj.SendReplyProto(jobs_pb2.ClientInformation())
    flow_obj.SendReplyProto(jobs_pb2.StartupInfo())
    flow_obj.SendReplyProto(jobs_pb2.StartupInfo())
    flow_obj.SendReplyProto(jobs_pb2.StartupInfo(), tag="foo")
    flow_obj.PersistState()
    db.WriteFlowObject(mig_flow_objects.ToProtoFlow(flow_obj.rdf_flow))

    flow_2 = db.ReadFlowObject(client_id, self._FLOW_ID)
    result_metadata = flow_2.result_metadata

    self.assertIsInstance(result_metadata, flows_pb2.FlowResultMetadata)
    self.assertTrue(result_metadata.is_metadata_set)
    self.assertLen(result_metadata.num_results_per_type_tag, 3)

    sorted_counts = sorted(
        result_metadata.num_results_per_type_tag, key=lambda v: (v.type, v.tag)
    )
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
      self, db: abstract_db.Database
  ):
    client_id = db_test_utils.InitializeClient(db)

    flow = rdf_flow_objects.Flow()
    flow.client_id = client_id
    flow.flow_id = self._FLOW_ID
    db.WriteFlowObject(mig_flow_objects.ToProtoFlow(flow))

    flow_obj = FlowBaseTest.Flow(flow)
    flow_obj.SendReply(rdf_client.ClientInformation())
    flow_obj.PersistState()
    flow_obj.PersistState()
    db.WriteFlowObject(mig_flow_objects.ToProtoFlow(flow_obj.rdf_flow))

    flow_2 = db.ReadFlowObject(client_id, self._FLOW_ID)
    result_metadata = flow_2.result_metadata

    self.assertLen(result_metadata.num_results_per_type_tag, 1)
    self.assertTrue(result_metadata.is_metadata_set)
    self.assertEqual(
        result_metadata.num_results_per_type_tag[0].type, "ClientInformation"
    )
    self.assertEqual(result_metadata.num_results_per_type_tag[0].tag, "")
    self.assertEqual(result_metadata.num_results_per_type_tag[0].count, 1)

  @db_test_lib.WithDatabase
  def testResultMetadataAreCorrectlyUpdatedAfterMultiplePersistStateCallsProto(
      self, db: abstract_db.Database
  ):
    client_id = db_test_utils.InitializeClient(db)

    class ClientInfoSendReplyProto(flow_base.FlowBase):
      proto_result_types = [jobs_pb2.ClientInformation]

    flow = rdf_flow_objects.Flow()
    flow.client_id = client_id
    flow.flow_id = self._FLOW_ID
    db.WriteFlowObject(mig_flow_objects.ToProtoFlow(flow))

    flow_obj = ClientInfoSendReplyProto(flow)
    flow_obj.SendReplyProto(jobs_pb2.ClientInformation())
    flow_obj.PersistState()
    flow_obj.PersistState()
    db.WriteFlowObject(mig_flow_objects.ToProtoFlow(flow_obj.rdf_flow))

    flow_2 = db.ReadFlowObject(client_id, self._FLOW_ID)
    result_metadata = flow_2.result_metadata

    self.assertLen(result_metadata.num_results_per_type_tag, 1)
    self.assertTrue(result_metadata.is_metadata_set)
    self.assertEqual(
        result_metadata.num_results_per_type_tag[0].type, "ClientInformation"
    )
    self.assertEqual(result_metadata.num_results_per_type_tag[0].tag, "")
    self.assertEqual(result_metadata.num_results_per_type_tag[0].count, 1)

  @db_test_lib.WithDatabase
  def testSendReplyProtoStoresResults(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeClient(db)

    class ClientInfoResultFlow(flow_base.FlowBase):
      proto_result_types = [jobs_pb2.ClientInformation]

    flow = rdf_flow_objects.Flow()
    flow.client_id = client_id
    flow.flow_id = self._FLOW_ID
    proto_flow = mig_flow_objects.ToProtoFlow(flow)
    db.WriteFlowObject(proto_flow)

    flow_obj = ClientInfoResultFlow(flow)
    flow_obj.SendReplyProto(jobs_pb2.ClientInformation(client_name="foo"))
    flow_obj.PersistState()
    flow_obj.FlushQueuedMessages()

    db.WriteFlowObject(mig_flow_objects.ToProtoFlow(flow_obj.rdf_flow))

    flow_2 = db.ReadFlowObject(client_id, self._FLOW_ID)
    self.assertEqual(flow_2.num_replies_sent, 1)

    results = db.ReadFlowResults(client_id, self._FLOW_ID, 0, 10)
    self.assertLen(results, 1)
    payload = jobs_pb2.ClientInformation()
    results[0].payload.Unpack(payload)
    self.assertEqual(payload.client_name, "foo")

  @db_test_lib.WithDatabase
  def testSendReplyProtoRaisesIfNotProto(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeClient(db)

    class ClientInfoResultFlow1(flow_base.FlowBase):
      proto_result_types = [jobs_pb2.ClientInformation]

    flow = rdf_flow_objects.Flow()
    flow.client_id = client_id
    flow.flow_id = self._FLOW_ID
    db.WriteFlowObject(mig_flow_objects.ToProtoFlow(flow))

    flow_obj = ClientInfoResultFlow1(flow)

    with self.assertRaisesRegex(
        TypeError, "SendReplyProto can only send Protobufs"
    ):
      flow_obj.SendReplyProto(rdf_client.ClientInformation())  # pytype: disable=wrong-arg-types

  @db_test_lib.WithDatabase
  def testSendReplyProtoRaisesIfWrongType(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeClient(db)

    class ClientInfoResultFlow2(flow_base.FlowBase):
      proto_result_types = [jobs_pb2.ClientInformation]

    flow = rdf_flow_objects.Flow()
    flow.client_id = client_id
    flow.flow_id = self._FLOW_ID
    db.WriteFlowObject(mig_flow_objects.ToProtoFlow(flow))

    flow_obj = ClientInfoResultFlow2(flow)

    with self.assertRaisesRegex(
        TypeError, ".*sends response of unexpected type.*"
    ):
      flow_obj.SendReplyProto(jobs_pb2.StartupInfo())  # Not ClientInformation

  def testRunStateMethodStaticAnyResponse(self):
    # TODO: Remove once the "default" instance is actually default.
    try:
      instance = stats_collector_instance.Get()
      self.addCleanup(lambda: stats_collector_instance.Set(instance))
    except stats_collector_instance.StatsNotInitializedError:
      pass
    stats_collector_instance.Set(
        default_stats_collector.DefaultStatsCollector()
    )

    client_id = "C.0123456789ABCDEF"
    flow_id = "ABCDEFABCDEF"

    # A response to which `HandleFakeResponses` should put unpacked response.
    expected_response = wrappers_pb2.StringValue(value="Lorem ipsum.")
    handled_response = wrappers_pb2.StringValue()

    # TODO: Ideally, this should be named as `FakeFlow`, but some
    # other tests may already used this name and because of the magic of the
    # metaclass registry we cannot reuse class names, we have to be a bit more
    # inventive here.
    class FakeStateMethodFlow(flow_base.FlowBase):

      @flow_base.UseProto2AnyResponses
      def FakeState(
          self,
          responses: flow_responses.Responses[any_pb2.Any],
      ) -> None:
        if not responses.success:
          raise AssertionError("Unsuccessful responses")

        if len(responses) != 1:
          raise AssertionError("Unexpected number of responses")

        handled_response.ParseFromString(list(responses)[0].value)

    rdf_flow = rdf_flow_objects.Flow()
    rdf_flow.client_id = client_id
    rdf_flow.flow_id = flow_id

    flow = FakeStateMethodFlow(rdf_flow)

    response = rdf_flow_objects.FlowResponse()
    response.any_payload = rdf_structs.AnyValue.PackProto2(expected_response)

    status_response = rdf_flow_objects.FlowStatus()
    status_response.status = rdf_flow_objects.FlowStatus.Status.OK

    responses = [
        response,
        status_response,
    ]
    flow.RunStateMethod(FakeStateMethodFlow.FakeState.__name__, None, responses)

    self.assertEqual(handled_response, expected_response)

  def testRunStateMethodStaticAnyResponseWithoutStatusShouldFail(self):
    # TODO: Remove once the "default" instance is actually default.
    try:
      instance = stats_collector_instance.Get()
      self.addCleanup(lambda: stats_collector_instance.Set(instance))
    except stats_collector_instance.StatsNotInitializedError:
      pass
    stats_collector_instance.Set(
        default_stats_collector.DefaultStatsCollector()
    )

    class FakeStateMethodFlowWillFail(flow_base.FlowBase):

      @flow_base.UseProto2AnyResponses
      def FakeStateFails(
          self,
          responses: flow_responses.Responses[any_pb2.Any],
      ) -> None:
        del responses  # Unused
        raise ValueError("We should not get here")

    rdf_flow = rdf_flow_objects.Flow()
    rdf_flow.client_id = "C.0123456789ABCDEF"
    rdf_flow.flow_id = "ABCDEFABCDEF"

    flow = FakeStateMethodFlowWillFail(rdf_flow)

    response = rdf_flow_objects.FlowResponse()
    response.any_payload = rdf_structs.AnyValue.PackProto2(
        wrappers_pb2.StringValue(value="Shouldn't matter")
    )
    responses_without_status = [response]
    # Responses without status should fail for `UseProto2AnyResponses`
    flow.RunStateMethod(
        FakeStateMethodFlowWillFail.FakeStateFails.__name__,
        None,
        responses_without_status,
    )

    # `flow_responses.Responses.FromResponsesProto2Any` should raise ValueError
    # in this case. However, `RunStateMethod` catches all exceptions and
    # puts them in the `error_message` field instead.
    self.assertEqual(flow.rdf_flow.error_message, "Missing status response")

  def testRunStateMethodStaticAnyResponseCallback(self):
    # TODO: Remove once the "default" instance is actually default.
    try:
      instance = stats_collector_instance.Get()
      self.addCleanup(lambda: stats_collector_instance.Set(instance))
    except stats_collector_instance.StatsNotInitializedError:
      pass
    stats_collector_instance.Set(
        default_stats_collector.DefaultStatsCollector()
    )

    # A response to which `HandleFakeResponses` should put unpacked response.
    expected_response = wrappers_pb2.StringValue(value="Lorem ipsum.")
    handled_response = wrappers_pb2.StringValue()

    class FakeStateCallbackMethodFlow(flow_base.FlowBase):

      @flow_base.UseProto2AnyResponsesCallback
      def FakeCallback(
          self,
          responses: flow_responses.Responses[any_pb2.Any],
      ) -> None:
        if not responses.success:
          raise AssertionError("Unsuccessful responses")

        if len(responses) != 1:
          raise AssertionError("Unexpected number of responses")

        handled_response.ParseFromString(list(responses)[0].value)

    rdf_flow = rdf_flow_objects.Flow()
    rdf_flow.client_id = "C.0123456789ABCDEF"
    rdf_flow.flow_id = "ABCDEFABCDEF"

    flow = FakeStateCallbackMethodFlow(rdf_flow)

    response = rdf_flow_objects.FlowResponse()
    response.any_payload = rdf_structs.AnyValue.PackProto2(expected_response)
    responses_without_status = [response]
    # Responses without status shouldn't fail for
    # `UseProto2AnyResponsesCallback`
    flow.RunStateMethod(
        FakeStateCallbackMethodFlow.FakeCallback.__name__,
        None,
        responses_without_status,
    )

    self.assertEqual(handled_response, expected_response)

  @db_test_lib.WithDatabase
  def testCallRRGUnsupported(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeClient(db)
    flow_id = db_test_utils.InitializeFlow(db, client_id)

    rdf_flow = rdf_flow_objects.Flow()
    rdf_flow.client_id = client_id
    rdf_flow.flow_id = flow_id

    flow = FlowBaseTest.Flow(rdf_flow)

    with self.assertRaises(flow_base.RRGUnsupportedError):
      flow.CallRRG(rrg_pb2.GET_SYSTEM_METADATA, empty_pb2.Empty())

  @db_test_lib.WithDatabase
  def testCallRRGSupported(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(db)
    flow_id = db_test_utils.InitializeFlow(db, client_id)

    rdf_flow = rdf_flow_objects.Flow()
    rdf_flow.client_id = client_id
    rdf_flow.flow_id = flow_id

    flow = FlowBaseTest.Flow(rdf_flow)

    # We do not make any explicit assertions on particular flow requests or RRG
    # requests being somewhere or not as these should be considered details of
    # the implementation of the flow runner—we just want to have reasonable code
    # coverage and ensure that the call does not fail.
    flow.CallRRG(rrg_pb2.GET_SYSTEM_METADATA, empty_pb2.Empty())

  @db_test_lib.WithDatabase
  def testCallRRGFilters(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(db)
    flow_id = db_test_utils.InitializeFlow(db, client_id)

    rdf_flow = rdf_flow_objects.Flow()
    rdf_flow.client_id = client_id
    rdf_flow.flow_id = flow_id

    flow = FlowBaseTest.Flow(rdf_flow)

    args = empty_pb2.Empty()

    rrg_filter = rrg_pb2.Filter()
    rrg_filter.conditions.add(bool_equal=True)
    rrg_filter.conditions.add(string_match="fo+ba(r|z)")

    # We do not make any explicit assertions on particular flow requests or RRG
    # requests being somewhere or not as these should be considered details of
    # the implementation of the flow runner—we just want to have reasonable code
    # coverage and ensure that the call does not fail.
    flow.CallRRG(rrg_pb2.LIST_MOUNTS, args, filters=[rrg_filter])

  @db_test_lib.WithDatabase
  def testCallRRGContext(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(db)
    flow_id = db_test_utils.InitializeFlow(db, client_id)

    rdf_flow = rdf_flow_objects.Flow()
    rdf_flow.client_id = client_id
    rdf_flow.flow_id = flow_id

    args = empty_pb2.Empty()

    # We do not make any explicit assertions on particular flow requests or RRG
    # requests being somewhere or not as these should be considered details of
    # the implementation of the flow runner—we just want to have reasonable code
    # coverage and ensure that the call does not fail.
    flow = FlowBaseTest.Flow(rdf_flow)
    flow.CallRRG(rrg_pb2.GET_SYSTEM_METADATA, args, context={"foo": "bar"})

  def setupFlow(self, db: abstract_db.Database) -> flow_base.FlowBase:
    client_id = db_test_utils.InitializeClient(db)

    rdf_flow = rdf_flow_objects.Flow()
    rdf_flow.client_id = client_id
    rdf_flow.flow_id = self._FLOW_ID

    flow = FlowBaseTest.Flow(rdf_flow)
    return flow

  def setupFakeCounter(self) -> metrics.Counter:
    with self.SetUpStatsCollector(
        default_stats_collector.DefaultStatsCollector()
    ):
      fake_counter = metrics.Counter(
          "fake",
          fields=[("flow", str), ("hierarchy", str), ("exception", str)],
      )
      # This counter is used in an unrelated part of the code, but needs to be
      # initialized within this context too to avoid a failure that the counter
      # is not initialized. It's a counter used in the logging code.
      # TODO: Update test setup to allow overriding particular
      # counters without interfering with other counters.
      metrics.Counter("log_calls", fields=[("level", str)])
    return fake_counter

  @db_test_lib.WithDatabase
  def testErrorIncrementsMetricsWithExceptionName_OnlyErrorMessage(
      self, db: abstract_db.Database
  ):
    flow = self.setupFlow(db)
    fake_counter = self.setupFakeCounter()
    with mock.patch.object(flow_base, "FLOW_ERRORS", fake_counter):
      # Make sure counter is set to zero
      self.assertEqual(
          0,
          fake_counter.GetValue(fields=["Flow", False, "ErrorException"]),
      )
      flow.Error(
          error_message="raise ErrorException('should get this one')",
      )

    self.assertEqual(
        1,
        fake_counter.GetValue(fields=["Flow", False, "ErrorException"]),
    )

  @db_test_lib.WithDatabase
  def testErrorIncrementsMetricsWithExceptionName_OnlyBacktrace(
      self, db: abstract_db.Database
  ):
    flow = self.setupFlow(db)
    fake_counter = self.setupFakeCounter()
    with mock.patch.object(flow_base, "FLOW_ERRORS", fake_counter):
      # Make sure counter is set to zero
      self.assertEqual(
          0,
          fake_counter.GetValue(fields=["Flow", False, "BacktraceException"]),
      )
      flow.Error(
          backtrace="raise BacktraceException('should get this one')",
      )

    self.assertEqual(
        1,
        fake_counter.GetValue(fields=["Flow", False, "BacktraceException"]),
    )

  @db_test_lib.WithDatabase
  def testErrorIncrementsMetricsWithExceptionName_BothFields(
      self, db: abstract_db.Database
  ):
    flow = self.setupFlow(db)
    fake_counter = self.setupFakeCounter()
    with mock.patch.object(flow_base, "FLOW_ERRORS", fake_counter):
      # Make sure counter is set to zero
      self.assertEqual(
          0,
          fake_counter.GetValue(fields=["Flow", False, "Ignored"]),
      )
      self.assertEqual(
          0,
          fake_counter.GetValue(fields=["Flow", False, "BacktraceException"]),
      )
      flow.Error(
          error_message="raise Ignored('should ignore this one')",
          backtrace="raise BacktraceException('should get this one')",
      )
    self.assertEqual(
        0,
        fake_counter.GetValue(fields=["Flow", False, "Ignored"]),
    )
    self.assertEqual(
        1,
        fake_counter.GetValue(fields=["Flow", False, "BacktraceException"]),
    )

  @db_test_lib.WithDatabase
  def testErrorIncrementsMetricsWithExceptionName_MultipleMatches(
      self, db: abstract_db.Database
  ):
    flow = self.setupFlow(db)
    fake_counter = self.setupFakeCounter()
    with mock.patch.object(flow_base, "FLOW_ERRORS", fake_counter):
      # Make sure counter is set to zero
      self.assertEqual(
          0,
          fake_counter.GetValue(fields=["Flow", False, "Ignored"]),
      )
      self.assertEqual(
          0,
          fake_counter.GetValue(fields=["Flow", False, "BacktraceException"]),
      )
      # In case of multiple matches, the last one is used.
      flow.Error(
          error_message="raise Ignored('should ignore this one')",
          backtrace=(
              "raise Ignored('should ignore this one') some\n\nother\ntext"
              " raise package.grr.BacktraceException('should get this one')"
          ),
      )
    self.assertEqual(
        0,
        fake_counter.GetValue(fields=["Flow", False, "Ignored"]),
    )
    self.assertEqual(
        1,
        fake_counter.GetValue(fields=["Flow", False, "BacktraceException"]),
    )

  @db_test_lib.WithDatabase
  def testErrorIncrementsMetricsNoMatch(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeClient(db)

    rdf_flow = rdf_flow_objects.Flow()
    rdf_flow.client_id = client_id
    rdf_flow.flow_id = self._FLOW_ID

    flow = FlowBaseTest.Flow(rdf_flow)

    with self.SetUpStatsCollector(
        default_stats_collector.DefaultStatsCollector()
    ):
      fake_counter = metrics.Counter(
          "fake",
          fields=[("flow", str), ("is_child", bool), ("exception", str)],
      )
    with mock.patch.object(flow_base, "FLOW_ERRORS", fake_counter):
      # Make sure counter is set to zero
      self.assertEqual(
          0,
          fake_counter.GetValue(fields=["Flow", False, "Unknown"]),
      )
      # Flow fails with error msg
      flow.Error("Doesn't match the regex")

    self.assertEqual(
        1,
        fake_counter.GetValue(fields=["Flow", False, "Unknown"]),
    )

  @db_test_lib.WithDatabase
  def testErrorIncrementsMetricsNoName(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeClient(db)

    rdf_flow = rdf_flow_objects.Flow()
    rdf_flow.client_id = client_id
    rdf_flow.flow_id = self._FLOW_ID

    flow = FlowBaseTest.Flow(rdf_flow)

    with self.SetUpStatsCollector(
        default_stats_collector.DefaultStatsCollector()
    ):
      fake_counter = metrics.Counter(
          "fake",
          fields=[("flow", str), ("is_child", bool), ("exception", str)],
      )
    with mock.patch.object(flow_base, "FLOW_ERRORS", fake_counter):
      # Make sure counter is set to zero
      self.assertEqual(
          0,
          fake_counter.GetValue(fields=["Flow", False, "Unknown"]),
      )
      # Flow fails with error msg
      flow.Error()

    self.assertEqual(
        1,
        fake_counter.GetValue(fields=["Flow", False, "Unknown"]),
    )

  @db_test_lib.WithDatabase
  def testErrorIncrementsMetricsChild(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeClient(db)

    rdf_flow = rdf_flow_objects.Flow()
    rdf_flow.client_id = client_id
    rdf_flow.flow_id = self._FLOW_ID
    rdf_flow.parent_flow_id = "NOT EMPTY"

    flow = FlowBaseTest.Flow(rdf_flow)

    with self.SetUpStatsCollector(
        default_stats_collector.DefaultStatsCollector()
    ):
      fake_counter = metrics.Counter(
          "fake",
          fields=[("flow", str), ("is_child", bool), ("exception", str)],
      )
    with mock.patch.object(flow_base, "FLOW_ERRORS", fake_counter):
      # Make sure counter is set to zero
      self.assertEqual(
          0,
          fake_counter.GetValue(fields=["Flow", True, "Unknown"]),
      )
      # Flow fails with error msg
      flow.Error()

    self.assertEqual(
        1,
        fake_counter.GetValue(fields=["Flow", True, "Unknown"]),
    )

  @db_test_lib.WithDatabase
  def testProcessAllReadyRequests_CallsRunStateMethodForCompletedRequests(
      self, db: abstract_db.Database
  ):
    client_id = db_test_utils.InitializeClient(db)
    flow_id = db_test_utils.InitializeFlow(
        db,
        client_id,
        next_request_to_process=1,
        flow_state=rdf_flow_objects.Flow.FlowState.RUNNING,
    )

    requests = []
    for request_id in [1, 2]:
      requests.append(
          flows_pb2.FlowRequest(
              client_id=client_id,
              flow_id=flow_id,
              request_id=request_id,
              needs_processing=True,
              next_state="NextState",
          )
      )
    db.WriteFlowRequests(requests)

    # Request 2 has some responses.
    responses = [
        flows_pb2.FlowResponse(
            client_id=client_id, flow_id=flow_id, request_id=2, response_id=i
        )
        for i in [1, 2, 3]
    ]
    db.WriteFlowResponses(responses)

    rdf_flow = mig_flow_objects.ToRDFFlow(db.ReadFlowObject(client_id, flow_id))
    flow = FlowBaseTest.Flow(rdf_flow)

    with mock.patch.object(flow, "RunStateMethod") as mock_run_state_method:
      num_processed, num_incremental = flow.ProcessAllReadyRequests()
      self.assertEqual(num_processed, 2)
      self.assertEqual(num_incremental, 0)

      self.assertEqual(mock_run_state_method.call_count, 2)

      # Complete call for request 1.
      next_state, request_1, responses_1 = mock_run_state_method.mock_calls[
          0
      ].args
      self.assertEqual(next_state, "NextState")
      self.assertEqual(request_1.request_id, 1)
      self.assertIsNone(responses_1)
      # Complete call for request 2.
      next_state, request_2, responses_2 = mock_run_state_method.mock_calls[
          1
      ].args
      self.assertEqual(next_state, "NextState")
      self.assertEqual(request_2.request_id, 2)
      self.assertEqual([r.response_id for r in responses_2], [1, 2, 3])

  @db_test_lib.WithDatabase
  def testProcessAllReadyRequests_CallsRunStateMethodForIncrementalRequests(
      self, db: abstract_db.Database
  ):
    client_id = db_test_utils.InitializeClient(db)
    flow_id = db_test_utils.InitializeFlow(
        db,
        client_id,
        next_request_to_process=1,
        flow_state=rdf_flow_objects.Flow.FlowState.RUNNING,
    )

    requests = []
    for request_id in [1, 2]:
      requests.append(
          # Not complete request; incremental responses.
          flows_pb2.FlowRequest(
              client_id=client_id,
              flow_id=flow_id,
              request_id=request_id,
              needs_processing=False,
              callback_state="CallbackState",
          )
      )
    db.WriteFlowRequests(requests)

    # Request 2 has some responses.
    responses = [
        flows_pb2.FlowResponse(
            client_id=client_id, flow_id=flow_id, request_id=2, response_id=i
        )
        for i in [1, 2, 3]
    ]
    db.WriteFlowResponses(responses)

    rdf_flow = mig_flow_objects.ToRDFFlow(db.ReadFlowObject(client_id, flow_id))
    flow = FlowBaseTest.Flow(rdf_flow)

    with mock.patch.object(flow, "RunStateMethod") as mock_run_state_method:
      num_processed, num_incremental = flow.ProcessAllReadyRequests()
      self.assertEqual(num_processed, 0)
      # First request is incremental but has no responses yet.
      self.assertEqual(num_incremental, 2)

      self.assertEqual(mock_run_state_method.call_count, 1)
      callback, request_1, responses_1 = mock_run_state_method.mock_calls[
          0
      ].args
      self.assertEqual(callback, "CallbackState")
      self.assertEqual(request_1.request_id, 2)
      self.assertEqual([r.response_id for r in responses_1], [1, 2, 3])

  @db_test_lib.WithDatabase
  def testProcessAllReadyRequests_CallsRunStateMethodForIncrementalAndCompleteRequests(
      self, db: abstract_db.Database
  ):
    client_id = db_test_utils.InitializeClient(db)
    flow_id = db_test_utils.InitializeFlow(
        db,
        client_id,
        next_request_to_process=1,
        flow_state=rdf_flow_objects.Flow.FlowState.RUNNING,
    )

    requests = [
        # Complete request; incremental responses.
        flows_pb2.FlowRequest(
            client_id=client_id,
            flow_id=flow_id,
            request_id=1,
            needs_processing=True,
            callback_state="CallbackState_1",
            next_state="NextState_1",
            next_response_id=3,
        ),
        # Complete request; incremental responses.
        flows_pb2.FlowRequest(
            client_id=client_id,
            flow_id=flow_id,
            request_id=2,
            needs_processing=True,
            callback_state="CallbackState_2",
            next_state="NextState_2",
            next_response_id=1,
        ),
        # Not complete request; incremental responses.
        flows_pb2.FlowRequest(
            client_id=client_id,
            flow_id=flow_id,
            request_id=3,
            needs_processing=False,
            callback_state="CallbackState_3",
            next_state="NextState_3",
            next_response_id=2,
        ),
    ]
    db.WriteFlowRequests(requests)

    responses = []
    for request in requests:
      for response_id in [1, 2, 3]:
        responses.append(
            flows_pb2.FlowResponse(
                client_id=client_id,
                flow_id=flow_id,
                request_id=request.request_id,
                response_id=response_id,
            )
        )
    db.WriteFlowResponses(responses)

    rdf_flow = mig_flow_objects.ToRDFFlow(db.ReadFlowObject(client_id, flow_id))
    flow = FlowBaseTest.Flow(rdf_flow)

    with mock.patch.object(flow, "RunStateMethod") as mock_run_state_method:
      num_processed, num_incremental = flow.ProcessAllReadyRequests()

      self.assertEqual(num_processed, 2)
      self.assertEqual(num_incremental, 3)
      self.assertEqual(mock_run_state_method.call_count, 5)

      # Incremental call for request 1.
      callback, request, responses = mock_run_state_method.mock_calls[0].args
      self.assertEqual(callback, "CallbackState_1")
      self.assertEqual(request.request_id, 1)
      self.assertEqual([r.response_id for r in responses], [3])
      # Incremental call for request 2.
      callback, request, responses = mock_run_state_method.mock_calls[1].args
      self.assertEqual(callback, "CallbackState_2")
      self.assertEqual(request.request_id, 2)
      self.assertEqual([r.response_id for r in responses], [1, 2, 3])
      # Incremental call for request 3.
      callback, request, responses = mock_run_state_method.mock_calls[2].args
      self.assertEqual(callback, "CallbackState_3")
      self.assertEqual(request.request_id, 3)
      self.assertEqual([r.response_id for r in responses], [2, 3])
      # Complete call for request 1.
      next_state, request, responses = mock_run_state_method.mock_calls[3].args
      self.assertEqual(next_state, "NextState_1")
      self.assertEqual(request.request_id, 1)
      self.assertEqual([r.response_id for r in responses], [1, 2, 3])
      # Complete call for request 2.
      next_state, request, responses = mock_run_state_method.mock_calls[4].args
      self.assertEqual(next_state, "NextState_2")
      self.assertEqual(request.request_id, 2)
      self.assertEqual([r.response_id for r in responses], [1, 2, 3])

  @db_test_lib.WithDatabase
  def testProcessAllReadyRequests_CallsRunStateMethodForIncrementalAfterIncompleteRequests(
      self, db: abstract_db.Database
  ):
    client_id = db_test_utils.InitializeClient(db)
    flow_id = db_test_utils.InitializeFlow(
        db,
        client_id,
        next_request_to_process=1,
        flow_state=rdf_flow_objects.Flow.FlowState.RUNNING,
    )

    requests = [
        # Not complete; no incremental responses.
        flows_pb2.FlowRequest(
            client_id=client_id,
            flow_id=flow_id,
            request_id=1,
            needs_processing=False,
        ),
        # Complete request; incremental responses.
        flows_pb2.FlowRequest(
            client_id=client_id,
            flow_id=flow_id,
            request_id=2,
            needs_processing=False,
            callback_state="CallbackState_2",
            next_state="NextState_2",
            next_response_id=2,
        ),
    ]
    db.WriteFlowRequests(requests)

    # Responses for request 2.
    responses_2 = [
        flows_pb2.FlowResponse(
            client_id=client_id, flow_id=flow_id, request_id=2, response_id=i
        )
        for i in [1, 2, 3]
    ]
    db.WriteFlowResponses(responses_2)

    rdf_flow = mig_flow_objects.ToRDFFlow(db.ReadFlowObject(client_id, flow_id))
    flow = FlowBaseTest.Flow(rdf_flow)

    with mock.patch.object(flow, "RunStateMethod") as mock_run_state_method:
      num_processed, num_incremental = flow.ProcessAllReadyRequests()

      self.assertEqual(num_processed, 0)
      self.assertEqual(num_incremental, 1)
      self.assertEqual(mock_run_state_method.call_count, 1)

      # Incremental call for request 2.
      callback, request, responses = mock_run_state_method.mock_calls[0].args
      self.assertEqual(callback, "CallbackState_2")
      self.assertEqual(request.request_id, 2)
      self.assertEqual([r.response_id for r in responses], [2, 3])

  @db_test_lib.WithDatabase
  def testProcessAllReadyRequests_IncrementsNextResponseId(
      self, db: abstract_db.Database
  ):
    client_id = db_test_utils.InitializeClient(db)
    flow_id = db_test_utils.InitializeFlow(
        db,
        client_id,
        next_request_to_process=1,
        flow_state=rdf_flow_objects.Flow.FlowState.RUNNING,
    )
    # Not complte request; incremental responses.
    request = flows_pb2.FlowRequest(
        client_id=client_id,
        flow_id=flow_id,
        request_id=1,
        needs_processing=False,
        callback_state="CallbackState",
        next_response_id=1,
    )
    db.WriteFlowRequests([request])

    response = flows_pb2.FlowResponse(
        client_id=client_id,
        flow_id=flow_id,
        request_id=request.request_id,
        response_id=1,
    )
    db.WriteFlowResponses([response])

    rdf_flow = mig_flow_objects.ToRDFFlow(db.ReadFlowObject(client_id, flow_id))
    flow = FlowBaseTest.Flow(rdf_flow)

    with mock.patch.object(flow, "RunStateMethod") as mock_run_state_method:
      _, num_incremental = flow.ProcessAllReadyRequests()
      self.assertEqual(num_incremental, 1)

      self.assertEqual(mock_run_state_method.call_count, 1)
      callback, request, responses = mock_run_state_method.mock_calls[0].args
      self.assertEqual(callback, "CallbackState")
      self.assertEqual(request.request_id, 1)
      self.assertEqual([r.response_id for r in responses], [1])

    more_responses = [
        flows_pb2.FlowResponse(
            client_id=client_id,
            flow_id=flow_id,
            request_id=request.request_id,
            response_id=response_id,
        )
        for response_id in [2, 3]
    ]
    db.WriteFlowResponses(more_responses)

    with mock.patch.object(flow, "RunStateMethod") as mock_run_state_method:
      _, num_incremental = flow.ProcessAllReadyRequests()
      self.assertEqual(num_incremental, 1)

      self.assertEqual(mock_run_state_method.call_count, 1)
      callback, request, responses = mock_run_state_method.mock_calls[0].args
      self.assertEqual(callback, "CallbackState")
      self.assertEqual(request.request_id, 1)
      self.assertEqual([r.response_id for r in responses], [2, 3])

  @db_test_lib.WithDatabase
  def testStore(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeClient(db)
    flow_id = db_test_utils.InitializeFlow(
        db,
        client_id,
        next_request_to_process=1,
        flow_state=rdf_flow_objects.Flow.FlowState.RUNNING,
    )
    rdf_flow = mig_flow_objects.ToRDFFlow(db.ReadFlowObject(client_id, flow_id))
    flow = FlowBaseTest.Flow(rdf_flow)

    self.assertEqual(flow.store, flows_pb2.DefaultFlowStore())


class FlowBaseImplementationTest(flow_test_lib.FlowTestsBaseclass):

  @classmethod
  def setUpClass(cls):
    super().setUpClass()
    testing_startup.TestInit()

  def setupAndRun(self, cls: type[flow_base.FlowBase]) -> flows_pb2.Flow:
    """Sets up and runs a flow of the given type."""
    assert data_store.REL_DB is not None
    db = data_store.REL_DB
    client_id = db_test_utils.InitializeClient(db)
    test_username = db_test_utils.InitializeUser(db)

    flow_id = flow_test_lib.StartAndRunFlow(
        cls,
        action_mocks.ActionMock(action_mocks.Store),
        client_id=client_id,
        creator=test_username,
    )

    return db.ReadFlowObject(client_id, flow_id)

  def testStorePersists_CallState(self):

    class StoreCallStateFlow(
        flow_base.FlowBase[
            flows_pb2.EmptyFlowArgs,
            tests_pb2.DummyFlowStore,
            flows_pb2.DefaultFlowProgress,
        ]
    ):
      """Dummy flow that uses store."""

      proto_store_type = tests_pb2.DummyFlowStore

      def Start(self) -> None:
        self.store.msg = "Hello from Start!"
        self.CallState(next_state="AfterCallState")

      def AfterCallState(self, responses=None):
        del responses
        assert self.store.msg == "Hello from Start!"
        self.store.msg = "Hello from AfterCallState!"

    flow = self.setupAndRun(StoreCallStateFlow)

    self.assertTrue(flow.HasField("store"))
    store = tests_pb2.DummyFlowStore()
    flow.store.Unpack(store)
    self.assertEqual(store.msg, "Hello from AfterCallState!")

  def testStorePersists_CallStateProto(self):

    class StoreCallStateProtoFlow(
        flow_base.FlowBase[
            flows_pb2.EmptyFlowArgs,
            tests_pb2.DummyFlowStore,
            flows_pb2.DefaultFlowProgress,
        ]
    ):
      """Dummy flow that uses store."""

      proto_store_type = tests_pb2.DummyFlowStore

      def Start(self) -> None:
        self.store.msg = "Hello from Start!"
        self.CallStateProto(next_state="AfterCallStateProto")

      def AfterCallStateProto(self, responses=None):
        del responses
        assert self.store.msg == "Hello from Start!"
        self.store.msg = "Hello from AfterCallStateProto!"

    flow = self.setupAndRun(StoreCallStateProtoFlow)

    self.assertTrue(flow.HasField("store"))
    store = tests_pb2.DummyFlowStore()
    flow.store.Unpack(store)
    self.assertEqual(store.msg, "Hello from AfterCallStateProto!")

  def testStorePersists_CallStateInline(self):

    class StoreCallStateInlineFlow(
        flow_base.FlowBase[
            flows_pb2.EmptyFlowArgs,
            tests_pb2.DummyFlowStore,
            flows_pb2.DefaultFlowProgress,
        ]
    ):
      """Dummy flow that uses store."""

      proto_store_type = tests_pb2.DummyFlowStore

      def Start(self) -> None:
        self.store.msg = "Hello from Start!"
        self.CallStateInline(next_state="AfterCallStateInline")

      def AfterCallStateInline(self, responses=None):
        del responses
        assert self.store.msg == "Hello from Start!"
        self.store.msg = "Hello from AfterCallStateInline!"

    flow = self.setupAndRun(StoreCallStateInlineFlow)

    self.assertTrue(flow.HasField("store"))
    store = tests_pb2.DummyFlowStore()
    flow.store.Unpack(store)
    self.assertEqual(store.msg, "Hello from AfterCallStateInline!")

  def testStorePersists_CallStateInlineProto(self):

    class StoreCallStateInlineProtoFlow(
        flow_base.FlowBase[
            flows_pb2.EmptyFlowArgs,
            tests_pb2.DummyFlowStore,
            flows_pb2.DefaultFlowProgress,
        ]
    ):
      """Dummy flow that uses store."""

      proto_store_type = tests_pb2.DummyFlowStore

      def Start(self) -> None:
        self.store.msg = "Hello from Start!"
        self.CallStateInlineProto(next_state="AfterCallStateInlineProto")

      @flow_base.UseProto2AnyResponses
      def AfterCallStateInlineProto(self, responses=None):
        del responses
        assert self.store.msg == "Hello from Start!"
        self.store.msg = "Hello from AfterCallStateInlineProto!"

    flow = self.setupAndRun(StoreCallStateInlineProtoFlow)

    self.assertTrue(flow.HasField("store"))
    store = tests_pb2.DummyFlowStore()
    flow.store.Unpack(store)
    self.assertEqual(store.msg, "Hello from AfterCallStateInlineProto!")

  def testStorePersists_CallStateInlineProtoWithResponses(self):

    class StoreCallStateInlineProtoWithResponsesFlow(
        flow_base.FlowBase[
            flows_pb2.EmptyFlowArgs,
            tests_pb2.DummyFlowStore,
            flows_pb2.DefaultFlowProgress,
        ]
    ):
      """Dummy flow that uses store."""

      proto_store_type = tests_pb2.DummyFlowStore

      def Start(self) -> None:
        self.store.msg = "Hello from Start!"
        self.CallStateInlineProtoWithResponses(
            next_state="AfterCallStateInlineProtoWithResponses"
        )

      @flow_base.UseProto2AnyResponses
      def AfterCallStateInlineProtoWithResponses(self, responses=None):
        del responses
        assert self.store.msg == "Hello from Start!"
        self.store.msg = "Hello from AfterCallStateInlineProtoWithResponses!"

    flow = self.setupAndRun(StoreCallStateInlineProtoWithResponsesFlow)

    self.assertTrue(flow.HasField("store"))
    store = tests_pb2.DummyFlowStore()
    flow.store.Unpack(store)
    self.assertEqual(
        store.msg, "Hello from AfterCallStateInlineProtoWithResponses!"
    )

  def testStorePersists_CallFlow(self):

    class StoreCallFlowFlow(
        flow_base.FlowBase[
            flows_pb2.EmptyFlowArgs,
            tests_pb2.DummyFlowStore,
            flows_pb2.DefaultFlowProgress,
        ]
    ):
      """Dummy flow that uses store."""

      proto_store_type = tests_pb2.DummyFlowStore

      def Start(self) -> None:
        self.store.msg = "Hello from Start!"
        self.CallFlow(
            flow_test_lib.DummyFlowWithSingleReply.__name__,
            next_state="AfterCallFlow",
        )

      def AfterCallFlow(self, responses=None):
        del responses
        assert self.store.msg == "Hello from Start!"
        self.store.msg = "Hello from AfterCallFlow!"

    flow = self.setupAndRun(StoreCallFlowFlow)

    self.assertTrue(flow.HasField("store"))
    store = tests_pb2.DummyFlowStore()
    flow.store.Unpack(store)
    self.assertEqual(store.msg, "Hello from AfterCallFlow!")

  def testStorePersists_CallFlowProto(self):

    class StoreCallFlowProtoFlow(
        flow_base.FlowBase[
            flows_pb2.EmptyFlowArgs,
            tests_pb2.DummyFlowStore,
            flows_pb2.DefaultFlowProgress,
        ]
    ):
      """Dummy flow that uses store."""

      proto_store_type = tests_pb2.DummyFlowStore

      def Start(self) -> None:
        self.store.msg = "Hello from Start!"
        self.CallFlowProto(
            flow_test_lib.DummyFlowWithSingleReply.__name__,
            next_state="AfterCallFlowProto",
        )

      def AfterCallFlowProto(self, responses=None):
        del responses
        assert self.store.msg == "Hello from Start!"
        self.store.msg = "Hello from AfterCallFlowProto!"

    flow = self.setupAndRun(StoreCallFlowProtoFlow)

    self.assertTrue(flow.HasField("store"))
    store = tests_pb2.DummyFlowStore()
    flow.store.Unpack(store)
    self.assertEqual(store.msg, "Hello from AfterCallFlowProto!")

  def testStorePersists_CallClient(self):

    class StoreCallClientFlow(
        flow_base.FlowBase[
            flows_pb2.EmptyFlowArgs,
            tests_pb2.DummyFlowStore,
            flows_pb2.DefaultFlowProgress,
        ]
    ):
      """Dummy flow that uses store."""

      proto_store_type = tests_pb2.DummyFlowStore

      def Start(self) -> None:
        self.store.msg = "Hello from Start!"
        self.CallClient(
            action_registry.ACTION_STUB_BY_ID["Store"],
            request=rdf_protodict.DataBlob(string="Hey!"),
            next_state="AfterCallClient",
        )

      def AfterCallClient(self, responses=None):
        del responses
        assert self.store.msg == "Hello from Start!"
        self.store.msg = "Hello from AfterCallClient!"

    flow = self.setupAndRun(StoreCallClientFlow)

    self.assertTrue(flow.HasField("store"))
    store = tests_pb2.DummyFlowStore()
    flow.store.Unpack(store)
    self.assertEqual(store.msg, "Hello from AfterCallClient!")

  def testStorePersists_CallClientProto(self):

    class StoreCallClientProtoFlow(
        flow_base.FlowBase[
            flows_pb2.EmptyFlowArgs,
            tests_pb2.DummyFlowStore,
            flows_pb2.DefaultFlowProgress,
        ]
    ):
      """Dummy flow that uses store."""

      proto_store_type = tests_pb2.DummyFlowStore

      def Start(self) -> None:
        self.store.msg = "Hello from Start!"
        self.CallClientProto(
            action_registry.ACTION_STUB_BY_ID["Store"],
            action_args=jobs_pb2.DataBlob(string="Hey!"),
            next_state="AfterCallClientProto",
        )

      def AfterCallClientProto(self, responses=None):
        del responses
        assert self.store.msg == "Hello from Start!"
        self.store.msg = "Hello from AfterCallClientProto!"

    flow = self.setupAndRun(StoreCallClientProtoFlow)

    self.assertTrue(flow.HasField("store"))
    store = tests_pb2.DummyFlowStore()
    flow.store.Unpack(store)
    self.assertEqual(store.msg, "Hello from AfterCallClientProto!")

  def testProgressIntegration_CallState(self):

    class ProgressCallStateFlow(
        flow_base.FlowBase[
            flows_pb2.EmptyFlowArgs,
            flows_pb2.DefaultFlowStore,
            tests_pb2.DummyFlowProgress,
        ]
    ):
      proto_progress_type = tests_pb2.DummyFlowProgress
      progress: tests_pb2.DummyFlowProgress

      def GetProgressProto(self) -> tests_pb2.DummyFlowProgress:
        return self.progress

      def Start(self) -> None:
        self.progress.status = "Hello from Start!"
        self.CallState(next_state="AfterCallState")

      def AfterCallState(self, responses=None):
        del responses
        assert self.GetProgressProto().status == "Hello from Start!"
        self.progress.status = "Hello from AfterCallState!"

    flow = self.setupAndRun(ProgressCallStateFlow)

    self.assertTrue(flow.HasField("progress"))
    progress = tests_pb2.DummyFlowProgress()
    flow.progress.Unpack(progress)
    self.assertEqual(progress.status, "Hello from AfterCallState!")

  def testProgressIntegration_CallStateProto(self):

    class ProgressCallStateProtoFlow(
        flow_base.FlowBase[
            flows_pb2.EmptyFlowArgs,
            flows_pb2.DefaultFlowStore,
            tests_pb2.DummyFlowProgress,
        ]
    ):
      proto_progress_type = tests_pb2.DummyFlowProgress
      progress: tests_pb2.DummyFlowProgress

      def GetProgressProto(self) -> tests_pb2.DummyFlowProgress:
        return self.progress

      def Start(self) -> None:
        self.progress.status = "Hello from Start!"
        self.CallStateProto(next_state="AfterCallStateProto")

      def AfterCallStateProto(self, responses=None):
        del responses
        assert self.GetProgressProto().status == "Hello from Start!"
        self.progress.status = "Hello from AfterCallStateProto!"

    flow = self.setupAndRun(ProgressCallStateProtoFlow)

    self.assertTrue(flow.HasField("progress"))
    progress = tests_pb2.DummyFlowProgress()
    flow.progress.Unpack(progress)
    self.assertEqual(progress.status, "Hello from AfterCallStateProto!")

  def testProgressIntegration_CallStateInline(self):

    class ProgressCallStateInlineFlow(
        flow_base.FlowBase[
            flows_pb2.EmptyFlowArgs,
            flows_pb2.DefaultFlowStore,
            tests_pb2.DummyFlowProgress,
        ]
    ):
      proto_progress_type = tests_pb2.DummyFlowProgress
      progress: tests_pb2.DummyFlowProgress

      def GetProgressProto(self) -> tests_pb2.DummyFlowProgress:
        return self.progress

      def Start(self) -> None:
        self.progress.status = "Hello from Start!"
        self.CallStateInline(next_state="AfterCallStateInline")

      def AfterCallStateInline(self, responses=None):
        del responses
        assert self.GetProgressProto().status == "Hello from Start!"
        self.progress.status = "Hello from AfterCallStateInline!"

    flow = self.setupAndRun(ProgressCallStateInlineFlow)

    self.assertTrue(flow.HasField("progress"))
    progress = tests_pb2.DummyFlowProgress()
    flow.progress.Unpack(progress)
    self.assertEqual(progress.status, "Hello from AfterCallStateInline!")

  def testProgressIntegration_CallFlow(self):

    class ProgressCallFlowFlow(
        flow_base.FlowBase[
            flows_pb2.EmptyFlowArgs,
            flows_pb2.DefaultFlowStore,
            tests_pb2.DummyFlowProgress,
        ]
    ):
      proto_progress_type = tests_pb2.DummyFlowProgress
      progress: tests_pb2.DummyFlowProgress

      def GetProgressProto(self) -> tests_pb2.DummyFlowProgress:
        return self.progress

      def Start(self) -> None:
        self.progress.status = "Hello from Start!"
        self.CallFlow(
            flow_test_lib.DummyFlowWithSingleReply.__name__,
            next_state="AfterCallFlow",
        )

      def AfterCallFlow(self, responses=None):
        del responses
        assert self.GetProgressProto().status == "Hello from Start!"
        self.progress.status = "Hello from AfterCallFlow!"

    flow = self.setupAndRun(ProgressCallFlowFlow)

    self.assertTrue(flow.HasField("progress"))
    progress = tests_pb2.DummyFlowProgress()
    flow.progress.Unpack(progress)
    self.assertEqual(progress.status, "Hello from AfterCallFlow!")

  def testProgressIntegration_CallFlowProto(self):

    class ProgressCallFlowProtoFlow(
        flow_base.FlowBase[
            flows_pb2.EmptyFlowArgs,
            flows_pb2.DefaultFlowStore,
            tests_pb2.DummyFlowProgress,
        ]
    ):
      proto_progress_type = tests_pb2.DummyFlowProgress
      progress: tests_pb2.DummyFlowProgress

      def GetProgressProto(self) -> tests_pb2.DummyFlowProgress:
        return self.progress

      def Start(self) -> None:
        self.progress.status = "Hello from Start!"
        self.CallFlowProto(
            flow_test_lib.DummyFlowWithSingleReply.__name__,
            next_state="AfterCallFlowProto",
        )

      def AfterCallFlowProto(self, responses=None):
        del responses
        assert self.GetProgressProto().status == "Hello from Start!"
        self.progress.status = "Hello from AfterCallFlowProto!"

    flow = self.setupAndRun(ProgressCallFlowProtoFlow)

    self.assertTrue(flow.HasField("progress"))
    progress = tests_pb2.DummyFlowProgress()
    flow.progress.Unpack(progress)
    self.assertEqual(progress.status, "Hello from AfterCallFlowProto!")

  def testProgressIntegration_CallClient(self):

    class ProgressCallClientFlow(
        flow_base.FlowBase[
            flows_pb2.EmptyFlowArgs,
            flows_pb2.DefaultFlowStore,
            tests_pb2.DummyFlowProgress,
        ]
    ):
      proto_progress_type = tests_pb2.DummyFlowProgress
      progress: tests_pb2.DummyFlowProgress

      def GetProgressProto(self) -> tests_pb2.DummyFlowProgress:
        return self.progress

      def Start(self) -> None:
        self.progress.status = "Hello from Start!"
        self.CallClient(
            action_registry.ACTION_STUB_BY_ID["Store"],
            request=rdf_protodict.DataBlob(string="Hey!"),
            next_state="AfterCallClient",
        )

      def AfterCallClient(self, responses=None):
        del responses
        assert self.GetProgressProto().status == "Hello from Start!"
        self.progress.status = "Hello from AfterCallClient!"

    flow = self.setupAndRun(ProgressCallClientFlow)

    self.assertTrue(flow.HasField("progress"))
    progress = tests_pb2.DummyFlowProgress()
    flow.progress.Unpack(progress)
    self.assertEqual(progress.status, "Hello from AfterCallClient!")

  def testProgressIntegration_CallClientProto(self):

    class ProgressCallClientProtoFlow(
        flow_base.FlowBase[
            flows_pb2.EmptyFlowArgs,
            flows_pb2.DefaultFlowStore,
            tests_pb2.DummyFlowProgress,
        ]
    ):
      proto_progress_type = tests_pb2.DummyFlowProgress
      progress: tests_pb2.DummyFlowProgress

      def GetProgressProto(self) -> tests_pb2.DummyFlowProgress:
        return self.progress

      def Start(self) -> None:
        self.progress.status = "Hello from Start!"
        self.CallClientProto(
            action_registry.ACTION_STUB_BY_ID["Store"],
            action_args=jobs_pb2.DataBlob(string="Hey!"),
            next_state="AfterCallClientProto",
        )

      def AfterCallClientProto(self, responses=None):
        del responses
        assert self.GetProgressProto().status == "Hello from Start!"
        self.progress.status = "Hello from AfterCallClientProto!"

    flow = self.setupAndRun(ProgressCallClientProtoFlow)

    self.assertTrue(flow.HasField("progress"))
    progress = tests_pb2.DummyFlowProgress()
    flow.progress.Unpack(progress)
    self.assertEqual(progress.status, "Hello from AfterCallClientProto!")

  def testCallStateInlineProtoWithResponses_AnyAndRequestData(self):
    class CallStateInlineResponsesAnyRequestData(flow_base.FlowBase):

      def Start(self) -> None:
        r1 = any_pb2.Any()
        r1.Pack(tests_pb2.ApiSingleStringArgument(arg="res1"))
        r2 = any_pb2.Any()
        r2.Pack(tests_pb2.ApiSingleStringArgument(arg="res2"))
        r3 = any_pb2.Any()
        r3.Pack(tests_pb2.ApiSingleStringArgument(arg="res3"))
        self.CallStateInlineProtoWithResponses(
            next_state="ReceiveInlineResponses",
            responses=flow_responses.FakeResponses(
                messages=[r1, r2, r3], request_data={"hello": "world"}
            ),
        )

      @flow_base.UseProto2AnyResponses
      def ReceiveInlineResponses(self, responses):
        assert responses.success
        assert len(responses) == 3
        response_list = list(responses)

        assert isinstance(response_list[0], any_pb2.Any)
        unpacked = tests_pb2.ApiSingleStringArgument()
        response_list[0].Unpack(unpacked)
        assert unpacked.arg == "res1"

        assert isinstance(response_list[1], any_pb2.Any)
        unpacked = tests_pb2.ApiSingleStringArgument()
        response_list[1].Unpack(unpacked)
        assert unpacked.arg == "res2"

        assert isinstance(response_list[2], any_pb2.Any)
        unpacked = tests_pb2.ApiSingleStringArgument()
        response_list[2].Unpack(unpacked)
        assert unpacked.arg == "res3"

        assert responses.request_data["hello"] == "world"

    assert data_store.REL_DB is not None
    db = data_store.REL_DB
    client_id = db_test_utils.InitializeClient(db)
    test_username = db_test_utils.InitializeUser(db, "test_username")

    flow_test_lib.StartAndRunFlow(
        CallStateInlineResponsesAnyRequestData,
        client_id=client_id,
        creator=test_username,
    )

  def testCallStateInlineProtoWithResponses_Unpacked(self):
    class CallStateInlineProtoResponsesUnpacked(flow_base.FlowBase):

      def Start(self) -> None:
        test_msgs = [
            tests_pb2.ApiSingleStringArgument(arg="res1"),
            tests_pb2.ApiSingleStringArgument(arg="res2"),
            tests_pb2.ApiSingleStringArgument(arg="res3"),
        ]
        self.CallStateInlineProtoWithResponses(
            next_state="UnpackedResponsesShouldFail",
            responses=flow_responses.FakeResponses(
                messages=test_msgs, request_data=None
            ),
        )

      @flow_base.UseProto2AnyResponses
      def UnpackedResponsesShouldFail(self, responses):
        raise NotImplementedError  # should not get here

    assert data_store.REL_DB is not None
    db = data_store.REL_DB
    client_id = db_test_utils.InitializeClient(db)
    test_username = db_test_utils.InitializeUser(db, "test_username")

    with self.assertRaisesRegex(
        RuntimeError,
        r".*Responses\[any_pb2.Any\].*",
    ):
      flow_test_lib.StartAndRunFlow(
          CallStateInlineProtoResponsesUnpacked,
          client_id=client_id,
          creator=test_username,
      )

  def testCallStateInlineProto_AnyRaises(self):
    class CallStateInlineProtoNoResponsesAny(flow_base.FlowBase):

      def Start(self) -> None:
        r1 = any_pb2.Any()
        r1.Pack(tests_pb2.ApiSingleStringArgument(arg="res1"))
        r2 = any_pb2.Any()
        r2.Pack(tests_pb2.ApiSingleStringArgument(arg="res2"))
        r3 = any_pb2.Any()
        r3.Pack(tests_pb2.ApiSingleStringArgument(arg="res3"))
        self.CallStateInlineProto(
            next_state="AnyShouldFail",
            messages=[r1, r2, r3],
        )

      @flow_base.UseProto2AnyResponses
      def AnyShouldFail(self, responses):
        raise NotImplementedError  # should not get here

    assert data_store.REL_DB is not None
    db = data_store.REL_DB
    client_id = db_test_utils.InitializeClient(db)
    test_username = db_test_utils.InitializeUser(db, "test_username")

    with self.assertRaisesRegex(
        RuntimeError,
        r".*Expected unpacked proto message but got an any_pb2.Any.*",
    ):
      flow_test_lib.StartAndRunFlow(
          CallStateInlineProtoNoResponsesAny,
          client_id=client_id,
          creator=test_username,
      )

  def testCallStateInlineProto_Unpacked(self):
    class CallStateInlineProtoNoResponsesPacked(flow_base.FlowBase):

      def Start(self) -> None:
        unpacked_msgs = [
            tests_pb2.ApiSingleStringArgument(arg="res1"),
            tests_pb2.ApiSingleStringArgument(arg="res2"),
            tests_pb2.ApiSingleStringArgument(arg="res3"),
        ]
        self.CallStateInlineProto(
            next_state="ReceiveInlineResponses",
            messages=unpacked_msgs,
            request_data={"hello": "world"},
        )

      @flow_base.UseProto2AnyResponses
      def ReceiveInlineResponses(self, responses):
        assert responses.success
        assert len(responses) == 3
        response_list = list(responses)

        assert isinstance(response_list[0], any_pb2.Any)
        unpacked = tests_pb2.ApiSingleStringArgument()
        response_list[0].Unpack(unpacked)
        assert unpacked.arg == "res1"

        assert isinstance(response_list[1], any_pb2.Any)
        unpacked = tests_pb2.ApiSingleStringArgument()
        response_list[1].Unpack(unpacked)
        assert unpacked.arg == "res2"

        assert isinstance(response_list[2], any_pb2.Any)
        unpacked = tests_pb2.ApiSingleStringArgument()
        response_list[2].Unpack(unpacked)
        assert unpacked.arg == "res3"

        assert responses.request_data["hello"] == "world"

    assert data_store.REL_DB is not None
    db = data_store.REL_DB
    client_id = db_test_utils.InitializeClient(db)
    test_username = db_test_utils.InitializeUser(db, "test_username")

    flow_test_lib.StartAndRunFlow(
        CallStateInlineProtoNoResponsesPacked,
        client_id=client_id,
        creator=test_username,
    )

  def testCallStateInlineProto_UnmarkedState(self):
    class DummyCallStateInlineProtoNotAnnotated(flow_base.FlowBase):

      def Start(self) -> None:
        self.CallStateInlineProto(next_state="NotMarkedWithAnnotation")

      def NotMarkedWithAnnotation(self, responses):
        raise NotImplementedError  # should not get here

    assert data_store.REL_DB is not None
    db = data_store.REL_DB
    client_id = db_test_utils.InitializeClient(db)
    test_username = db_test_utils.InitializeUser(db, "test_username")

    with self.assertRaisesRegex(
        RuntimeError, r".*is not annotated with `@UseProto2AnyResponses`.*"
    ):
      flow_test_lib.StartAndRunFlow(
          DummyCallStateInlineProtoNotAnnotated,
          client_id=client_id,
          creator=test_username,
      )

  def testCallStateInlineProtoWithResponses_UnmarkedState(self):
    class DummyCallStateInlineProtoWithResponsesNotAnnotated(
        flow_base.FlowBase
    ):

      def Start(self) -> None:
        self.CallStateInlineProtoWithResponses(
            next_state="NotMarkedWithAnnotation"
        )

      def NotMarkedWithAnnotation(self, responses):
        raise NotImplementedError  # should not get here

    assert data_store.REL_DB is not None
    db = data_store.REL_DB
    client_id = db_test_utils.InitializeClient(db)
    test_username = db_test_utils.InitializeUser(db, "test_username")

    with self.assertRaisesRegex(
        RuntimeError, r".*is not annotated with `@UseProto2AnyResponses`.*"
    ):
      flow_test_lib.StartAndRunFlow(
          DummyCallStateInlineProtoWithResponsesNotAnnotated,
          client_id=client_id,
          creator=test_username,
      )

  def testCallStateProto_RequestData(self):

    class CallStateProtoWithRequestDataFlow(
        flow_base.FlowBase[
            flows_pb2.EmptyFlowArgs,
            flows_pb2.DefaultFlowStore,
            flows_pb2.DefaultFlowProgress,
        ]
    ):

      def Start(self) -> None:
        self.CallStateProto(
            next_state="AfterCallStateProto",
            request_data={
                "foo": "bar",
                "baz": 42,
            },
        )

      @flow_base.UseProto2AnyResponses
      def AfterCallStateProto(
          self,
          responses: flow_responses.Responses[any_pb2.Any],
      ) -> None:
        assert responses.request_data["foo"] == "bar"
        assert responses.request_data["baz"] == 42

    client_id = db_test_utils.InitializeRRGClient(data_store.REL_DB)

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=CallStateProtoWithRequestDataFlow,
        flow_args=rdf_flows.EmptyFlowArgs(),
        handlers={},
    )

    flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.backtrace, "")
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

  def testProtoArgsUpdate(self):

    class FlowArgumentsUpdate(
        flow_base.FlowBase[
            jobs_pb2.LogMessage,
            flows_pb2.DefaultFlowStore,
            flows_pb2.DefaultFlowProgress,
        ]
    ):
      args_type = rdf_client.LogMessage
      proto_args_type = jobs_pb2.LogMessage

      def Start(self):
        assert self.args.data == "foo"
        assert self.proto_args.data == "foo"

        # NOT replicated (field changed, not args itself)
        self.args.data = "bar"
        assert self.args.data == "bar"
        assert self.proto_args.data == "foo"

        # NOT replicated (field changed, not args itself)
        self.proto_args.data = "baz"
        assert self.proto_args.data == "baz"
        assert self.args.data == "bar"

        # Resets the pointer, should be replicated
        self.args = rdf_client.LogMessage(data="qux")
        assert self.args.data == "qux"
        assert self.proto_args.data == "qux"

        # Resets the pointer, should be replicated
        self.proto_args = jobs_pb2.LogMessage(data="norf")
        assert self.proto_args.data == "norf"
        assert self.args.data == "norf"

    assert data_store.REL_DB is not None
    db = data_store.REL_DB
    client_id = db_test_utils.InitializeClient(db)
    test_username = db_test_utils.InitializeUser(db, "test_username")

    flow_id = flow_test_lib.StartAndRunFlow(
        FlowArgumentsUpdate,
        client_id=client_id,
        creator=test_username,
        flow_args=rdf_client.LogMessage(data="foo"),
    )

    persisted_flow = db.ReadFlowObject(client_id, flow_id)
    args = jobs_pb2.LogMessage()
    persisted_flow.args.Unpack(args)
    self.assertEqual(args.data, "norf")


class FindFlowRequestsToProcessTest(absltest.TestCase):

  def testFindIncrementalRequestsToProcess(self):
    client_id = "client_id"
    flow_id = "flow_id"

    # Incremental request that was already processed.
    request_1 = flows_pb2.FlowRequest(
        client_id=client_id,
        flow_id=flow_id,
        request_id=1,
        callback_state="Callback_1",
        next_response_id=2,
        needs_processing=True,
    )
    responses_1 = [
        flows_pb2.FlowResponse(
            client_id=client_id,
            flow_id=flow_id,
            request_id=request_1.request_id,
            response_id=i,
        )
        for i in [1, 2]
    ]
    # Incremental request with new responses.
    request_2 = flows_pb2.FlowRequest(
        client_id=client_id,
        flow_id=flow_id,
        request_id=2,
        callback_state="Callback_2",
        next_response_id=2,
    )
    responses_2 = [
        flows_pb2.FlowResponse(
            client_id=client_id,
            flow_id=flow_id,
            request_id=request_2.request_id,
            response_id=i,
        )
        for i in [1, 2, 3]
    ]
    # Not incremental request with new responses.
    request_3 = flows_pb2.FlowRequest(
        client_id=client_id,
        flow_id=flow_id,
        request_id=3,
    )
    responses_3 = [
        flows_pb2.FlowResponse(
            client_id=client_id,
            flow_id=flow_id,
            request_id=request_3.request_id,
            response_id=i,
        )
        for i in [1, 2]
    ]
    # Incremental request with no new responses.
    request_4 = flows_pb2.FlowRequest(
        client_id=client_id,
        flow_id=flow_id,
        request_id=4,
        callback_state="Callback_4",
        next_response_id=2,
        needs_processing=True,
    )
    responses_4 = [
        flows_pb2.FlowResponse(
            client_id=client_id,
            flow_id=flow_id,
            request_id=request_4.request_id,
            response_id=1,
        )
    ]

    flow_requests = {
        request_1.request_id: (request_1, responses_1),
        request_2.request_id: (request_2, responses_2),
        request_3.request_id: (request_3, responses_3),
        request_4.request_id: (request_4, responses_4),
    }
    incremental_requests = flow_base.FindIncrementalRequestsToProcess(
        request_dict=flow_requests, next_needed_request_id=2
    )

    # Only requests 1, 2 and 4 are incremental, 1 is already processed,
    # 4 has no new responses.
    self.assertLen(incremental_requests, 1)
    req_2, resp_2 = incremental_requests[0]

    self.assertEqual(req_2.request_id, 2)
    self.assertEqual(req_2.flow_id, flow_id)
    self.assertEqual(req_2.client_id, client_id)
    self.assertEqual(req_2.callback_state, "Callback_2")
    self.assertEqual(req_2.next_response_id, 2)
    # Two new responses for request 1.
    self.assertLen(resp_2, 2)
    self.assertEqual(resp_2[0].response_id, 2)
    self.assertEqual(resp_2[1].response_id, 3)

  def testFindCompletedRequestsToProcess_ExcludeAfterIncompleteRequest(self):
    client_id = "client_id"
    flow_id = "flow_id"

    # Completed request with responses.
    request_1 = flows_pb2.FlowRequest(
        client_id=client_id,
        flow_id=flow_id,
        request_id=1,
        needs_processing=True,
    )
    responses_1 = [
        flows_pb2.FlowResponse(
            client_id=client_id,
            flow_id=flow_id,
            request_id=request_1.request_id,
            response_id=i,
        )
        for i in [1, 2]
    ]
    # Not Completed request with responses.
    request_2 = flows_pb2.FlowRequest(
        client_id=client_id,
        flow_id=flow_id,
        request_id=2,
    )
    responses_2 = [
        flows_pb2.FlowResponse(
            client_id=client_id,
            flow_id=flow_id,
            request_id=request_2.request_id,
            response_id=i,
        )
        for i in [1, 2, 3]
    ]
    # Completed request without responses.
    request_3 = flows_pb2.FlowRequest(
        client_id=client_id,
        flow_id=flow_id,
        request_id=3,
        needs_processing=True,
    )
    responses_3 = []

    flow_requests = {
        request_1.request_id: (request_1, responses_1),
        request_2.request_id: (request_2, responses_2),
        request_3.request_id: (request_3, responses_3),
    }
    completed_requests = flow_base.FindCompletedRequestsToProcess(
        request_dict=flow_requests, next_needed_request_id=1
    )

    # Requests 1, and 3 are completed, 2 is not yet complete so 3 cannot be
    # processed yet.
    self.assertLen(completed_requests, 1)

    # Request 1.
    req_1, resp_1 = completed_requests[0]
    self.assertEqual(req_1.request_id, 1)
    self.assertEqual(req_1.flow_id, flow_id)
    self.assertEqual(req_1.client_id, client_id)
    self.assertEqual(req_1.needs_processing, True)
    # All responses are returned, next_response_id is only for incremental
    # requests.
    self.assertLen(resp_1, 2)
    self.assertEqual(resp_1[0].response_id, 1)
    self.assertEqual(resp_1[1].response_id, 2)

  def testFindCompletedRequestsToProcess_ExcludeAfterMissingRequest(self):
    client_id = "client_id"
    flow_id = "flow_id"

    # Completed request with responses.
    request_1 = flows_pb2.FlowRequest(
        client_id=client_id,
        flow_id=flow_id,
        request_id=1,
        needs_processing=True,
    )
    responses_1 = [
        flows_pb2.FlowResponse(
            client_id=client_id,
            flow_id=flow_id,
            request_id=request_1.request_id,
            response_id=i,
        )
        for i in [1, 2]
    ]
    # Completed request with responses.
    request_2 = flows_pb2.FlowRequest(
        client_id=client_id,
        flow_id=flow_id,
        request_id=2,
        needs_processing=True,
        next_response_id=4,
    )
    responses_2 = [
        flows_pb2.FlowResponse(
            client_id=client_id,
            flow_id=flow_id,
            request_id=request_2.request_id,
            response_id=i,
        )
        for i in [1, 2, 3]
    ]
    # Completed request without responses.
    request_3 = flows_pb2.FlowRequest(
        client_id=client_id,
        flow_id=flow_id,
        request_id=3,
        needs_processing=True,
    )
    responses_3 = []
    # Missing request with id 4.

    # Completed request with responses.
    request_5 = flows_pb2.FlowRequest(
        client_id=client_id,
        flow_id=flow_id,
        request_id=5,
        needs_processing=True,
    )
    responses_5 = [
        flows_pb2.FlowResponse(
            client_id=client_id,
            flow_id=flow_id,
            request_id=request_5.request_id,
            response_id=1,
        )
    ]

    flow_requests = {
        request_1.request_id: (request_1, responses_1),
        request_2.request_id: (request_2, responses_2),
        request_3.request_id: (request_3, responses_3),
        # Missing request 4.
        request_5.request_id: (request_5, responses_5),
    }
    completed_requests = flow_base.FindCompletedRequestsToProcess(
        request_dict=flow_requests, next_needed_request_id=2
    )

    # Requests 1, 2, 3, and 5 are completed but 1 was already processed,
    # and 4 is missing, so 5 cannot be processed yet.
    self.assertLen(completed_requests, 2)

    # Request 2.
    req_2, resp_2 = completed_requests[0]
    self.assertEqual(req_2.request_id, 2)
    self.assertEqual(req_2.flow_id, flow_id)
    self.assertEqual(req_2.client_id, client_id)
    self.assertEqual(req_2.needs_processing, True)
    # All responses are returned, next_response_id is only for incremental
    # requests.
    self.assertLen(resp_2, 3)
    self.assertEqual(resp_2[0].response_id, 1)
    self.assertEqual(resp_2[1].response_id, 2)
    self.assertEqual(resp_2[2].response_id, 3)

    # Request 3.
    req_3, resp_3 = completed_requests[1]
    self.assertEqual(req_3.request_id, 3)
    self.assertEqual(req_3.flow_id, flow_id)
    self.assertEqual(req_3.client_id, client_id)
    self.assertEqual(req_3.needs_processing, True)
    self.assertEmpty(resp_3)


if __name__ == "__main__":
  absltest.main()
