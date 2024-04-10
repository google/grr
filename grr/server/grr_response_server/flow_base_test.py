#!/usr/bin/env python
from unittest import mock

from absl.testing import absltest

from google.protobuf import any_pb2
from google.protobuf import empty_pb2
from google.protobuf import wrappers_pb2
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.stats import default_stats_collector
from grr_response_core.stats import metrics
from grr_response_core.stats import stats_collector_instance
from grr_response_proto import jobs_pb2
from grr_response_server import flow_base
from grr_response_server import flow_responses
from grr_response_server.databases import db as abstract_db
from grr_response_server.databases import db_test_utils
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr_response_server.rdfvalues import mig_flow_objects
from grr.test_lib import db_test_lib
from grr.test_lib import stats_test_lib
from grr_response_proto import rrg_pb2


class FlowBaseTest(absltest.TestCase, stats_test_lib.StatsCollectorTestMixin):

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
  def testPythonAgentSupportFalse(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(db)

    flow = rdf_flow_objects.Flow()
    flow.client_id = client_id
    flow.flow_id = self._FLOW_ID

    flow = FlowBaseTest.Flow(flow)
    self.assertFalse(flow.python_agent_support)

  @db_test_lib.WithDatabase
  def testPythoAgentSupportTrue(self, db: abstract_db.Database):
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
  def testRrgSupport(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(db)

    flow = rdf_flow_objects.Flow()
    flow.client_id = client_id
    flow.flow_id = self._FLOW_ID

    flow = FlowBaseTest.Flow(flow)
    self.assertTrue(flow.rrg_support, True)

  @db_test_lib.WithDatabase
  def testReturnsDefaultFlowProgressForEmptyFlow(self,
                                                 db: abstract_db.Database):
    client_id = db_test_utils.InitializeClient(db)

    flow = rdf_flow_objects.Flow()
    flow.client_id = client_id
    flow.flow_id = self._FLOW_ID
    db.WriteFlowObject(mig_flow_objects.ToProtoFlow(flow))

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
    db.WriteFlowObject(mig_flow_objects.ToProtoFlow(flow))

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
    db.WriteFlowObject(mig_flow_objects.ToProtoFlow(flow))

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
    db.WriteFlowObject(mig_flow_objects.ToProtoFlow(flow))

    flow_obj = FlowBaseTest.Flow(flow)
    flow_obj.SendReply(rdf_client.ClientInformation())
    flow_obj.SendReply(rdf_client.StartupInfo())
    flow_obj.SendReply(rdf_client.StartupInfo())
    flow_obj.SendReply(rdf_client.StartupInfo(), tag="foo")
    flow_obj.PersistState()
    db.WriteFlowObject(mig_flow_objects.ToProtoFlow(flow_obj.rdf_flow))

    flow_2 = db.ReadFlowObject(client_id, self._FLOW_ID)
    flow_2 = mig_flow_objects.ToRDFFlow(flow_2)
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
    db.WriteFlowObject(mig_flow_objects.ToProtoFlow(flow))

    flow_obj = FlowBaseTest.Flow(flow)
    flow_obj.SendReply(rdf_client.ClientInformation())
    flow_obj.PersistState()
    flow_obj.PersistState()
    db.WriteFlowObject(mig_flow_objects.ToProtoFlow(flow_obj.rdf_flow))

    flow_2 = db.ReadFlowObject(client_id, self._FLOW_ID)
    flow_2 = mig_flow_objects.ToRDFFlow(flow_2)
    flow_obj_2 = FlowBaseTest.Flow(flow_2)
    result_metadata = flow_obj_2.GetResultMetadata()

    self.assertLen(result_metadata.num_results_per_type_tag, 1)
    self.assertTrue(result_metadata.is_metadata_set)
    self.assertEqual(result_metadata.num_results_per_type_tag[0].type,
                     "ClientInformation")
    self.assertEqual(result_metadata.num_results_per_type_tag[0].tag, "")
    self.assertEqual(result_metadata.num_results_per_type_tag[0].count, 1)

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
  def testErrorIncrementsMetricsWithExceptionName(
      self, db: abstract_db.Database
  ):
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
          fields=[("flow", str), ("hierarchy", str), ("exception", str)],
      )
    with mock.patch.object(flow_base, "FLOW_ERRORS", fake_counter):
      # Make sure counter is set to zero
      self.assertEqual(
          0,
          fake_counter.GetValue(
              fields=["Flow", False, "ErrLooksLikeException"]
          ),
      )
      # Flow fails with error msg
      flow.Error("ErrLooksLikeException('should extract exception name')")

    self.assertEqual(
        1,
        fake_counter.GetValue(fields=["Flow", False, "ErrLooksLikeException"]),
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


if __name__ == "__main__":
  absltest.main()
