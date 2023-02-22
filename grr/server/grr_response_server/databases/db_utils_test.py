#!/usr/bin/env python
import logging
from unittest import mock

from absl import app
from absl.testing import absltest

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_server.databases import db
from grr_response_server.databases import db_utils
from grr_response_server.rdfvalues import objects as rdf_objects
from grr.test_lib import stats_test_lib
from grr.test_lib import test_lib


class BatchPlannerTest(absltest.TestCase):
  """Test class for OperatioBatcher."""

  def testSingleOperationLowerThanLimit(self):
    batch_planner = db_utils.BatchPlanner(10)
    batch_planner.PlanOperation("a", 9)

    self.assertEqual(batch_planner.batches, [
        [("a", 0, 9)],
    ])

  def testMultipleOperationsLowerThanLimitInTotal(self):
    batch_planner = db_utils.BatchPlanner(10)
    batch_planner.PlanOperation("a", 3)
    batch_planner.PlanOperation("b", 3)
    batch_planner.PlanOperation("c", 3)

    self.assertEqual(batch_planner.batches, [
        [("a", 0, 3), ("b", 0, 3), ("c", 0, 3)],
    ])

  def testSingleOperationBiggerThanLimit(self):
    batch_planner = db_utils.BatchPlanner(10)
    batch_planner.PlanOperation("a", 12)

    self.assertEqual(batch_planner.batches, [
        [("a", 0, 10)],
        [("a", 10, 2)],
    ])

  def testSingleOperationMoreThanTwiceBiggerThanLimit(self):
    batch_planner = db_utils.BatchPlanner(10)
    batch_planner.PlanOperation("a", 22)

    self.assertEqual(batch_planner.batches, [
        [("a", 0, 10)],
        [("a", 10, 10)],
        [("a", 20, 2)],
    ])

  def testMultipleOperationsBiggerThanLimitInTotal(self):
    batch_planner = db_utils.BatchPlanner(10)
    batch_planner.PlanOperation("a", 3)
    batch_planner.PlanOperation("b", 3)
    batch_planner.PlanOperation("c", 3)
    batch_planner.PlanOperation("d", 3)

    self.assertEqual(batch_planner.batches, [
        [("a", 0, 3), ("b", 0, 3), ("c", 0, 3), ("d", 0, 1)],
        [("d", 1, 2)],
    ])

  def testMultipleOperationsTwiceBiggerThanLimitInTotal(self):
    batch_planner = db_utils.BatchPlanner(10)
    batch_planner.PlanOperation("a", 3)
    batch_planner.PlanOperation("b", 3)
    batch_planner.PlanOperation("c", 3)
    batch_planner.PlanOperation("d", 3)
    batch_planner.PlanOperation("e", 3)
    batch_planner.PlanOperation("f", 3)
    batch_planner.PlanOperation("g", 3)

    self.assertEqual(batch_planner.batches, [
        [("a", 0, 3), ("b", 0, 3), ("c", 0, 3), ("d", 0, 1)],
        [("d", 1, 2), ("e", 0, 3), ("f", 0, 3), ("g", 0, 2)],
        [("g", 2, 1)],
    ])

  def testMultipleOperationsEachBiggerThanLimit(self):
    batch_planner = db_utils.BatchPlanner(10)
    batch_planner.PlanOperation("a", 12)
    batch_planner.PlanOperation("b", 12)

    self.assertEqual(batch_planner.batches, [
        [("a", 0, 10)],
        [("a", 10, 2), ("b", 0, 8)],
        [("b", 8, 4)],
    ])


class CallLoggedAndAccountedTest(stats_test_lib.StatsTestMixin,
                                 absltest.TestCase):

  @db_utils.CallLoggedAndAccounted
  def SampleCall(self):
    return 42

  @db_utils.CallLoggedAndAccounted
  def SampleCallWithGRRError(self):
    raise db.UnknownGRRUserError("Unknown")

  @db_utils.CallLoggedAndAccounted
  def SampleCallWithDBError(self):
    raise RuntimeError("some")

  def testReturnValueIsPropagated(self):
    self.assertEqual(self.SampleCall(), 42)

  def _ExpectIncrements(self, fn, latency_count_increment,
                        grr_errors_count_increment, db_errors_count_increment):

    with self.assertStatsCounterDelta(
        latency_count_increment,
        db_utils.DB_REQUEST_LATENCY,
        fields=[fn.__name__]):
      with self.assertStatsCounterDelta(
          grr_errors_count_increment,
          db_utils.DB_REQUEST_ERRORS,
          fields=[fn.__name__, "grr"]):
        with self.assertStatsCounterDelta(
            db_errors_count_increment,
            db_utils.DB_REQUEST_ERRORS,
            fields=[fn.__name__, "db"]):
          try:
            fn()
          except Exception:  # pylint: disable=broad-except
            pass

  def testSuccessIsAccounted(self):
    self._ExpectIncrements(self.SampleCall, 1, 0, 0)

  def testCallRaisingLogicalErrorIsCorretlyAccounted(self):
    self._ExpectIncrements(self.SampleCallWithGRRError, 0, 1, 0)

  def testCallRaisingRuntimeDBErrorIsCorretlyAccounted(self):
    self._ExpectIncrements(self.SampleCallWithDBError, 0, 0, 1)

  @mock.patch.object(logging, "debug")
  def testSuccessfulCallIsCorretlyLogged(self, debug_mock):
    self.SampleCall()

    self.assertTrue(debug_mock.called)
    got = debug_mock.call_args_list[0][0]
    self.assertIn("SUCCESS", got[0])
    self.assertEqual(got[1], "SampleCall")

  @mock.patch.object(logging, "debug")
  def testCallRaisingLogicalErrorIsCorretlyLogged(self, debug_mock):
    with self.assertRaises(db.UnknownGRRUserError):
      self.SampleCallWithGRRError()

    self.assertTrue(debug_mock.called)
    got = debug_mock.call_args_list[0][0]
    self.assertIn("GRR ERROR", got[0])
    self.assertEqual(got[1], "SampleCallWithGRRError")

  @mock.patch.object(logging, "debug")
  def testCallRaisingRuntimeDBErrorIsCorretlyLogged(self, debug_mock):
    with self.assertRaises(RuntimeError):
      self.SampleCallWithDBError()

    self.assertTrue(debug_mock.called)
    got = debug_mock.call_args_list[0][0]
    self.assertIn("INTERNAL DB ERROR", got[0])
    self.assertEqual(got[1], "SampleCallWithDBError")


class IdToIntConversionTest(absltest.TestCase):

  def testFlowIdToInt(self):
    self.assertEqual(db_utils.FlowIDToInt("00000001"), 1)
    self.assertEqual(db_utils.FlowIDToInt("1234ABCD"), 0x1234ABCD)
    self.assertEqual(db_utils.FlowIDToInt("FFFFFFFF"), 0xFFFFFFFF)
    self.assertEqual(db_utils.FlowIDToInt("0000000100000000"), 0x100000000)
    self.assertEqual(
        db_utils.FlowIDToInt("FFFFFFFFFFFFFFFF"), 0xFFFFFFFFFFFFFFFF)

  def testIntToFlowId(self):
    self.assertEqual(db_utils.IntToFlowID(1), "00000001")
    self.assertEqual(db_utils.IntToFlowID(0x1234ABCD), "1234ABCD")
    self.assertEqual(db_utils.IntToFlowID(0xFFFFFFFF), "FFFFFFFF")
    self.assertEqual(db_utils.IntToFlowID(0x100000000), "0000000100000000")
    self.assertEqual(
        db_utils.IntToFlowID(0xFFFFFFFFFFFFFFFF), "FFFFFFFFFFFFFFFF")

  def testHuntIdToInt(self):
    self.assertEqual(db_utils.HuntIDToInt("00000001"), 1)
    self.assertEqual(db_utils.HuntIDToInt("1234ABCD"), 0x1234ABCD)
    self.assertEqual(db_utils.HuntIDToInt("FFFFFFFF"), 0xFFFFFFFF)
    self.assertEqual(db_utils.HuntIDToInt("0000000100000000"), 0x100000000)
    self.assertEqual(
        db_utils.HuntIDToInt("FFFFFFFFFFFFFFFF"), 0xFFFFFFFFFFFFFFFF)

  def testIntToHuntId(self):
    self.assertEqual(db_utils.IntToHuntID(1), "00000001")
    self.assertEqual(db_utils.IntToHuntID(0x1234ABCD), "1234ABCD")
    self.assertEqual(db_utils.IntToHuntID(0xFFFFFFFF), "FFFFFFFF")
    self.assertEqual(db_utils.IntToHuntID(0x100000000), "0000000100000000")
    self.assertEqual(
        db_utils.IntToHuntID(0xFFFFFFFFFFFFFFFF), "FFFFFFFFFFFFFFFF")


class ParseAndUnpackAnyTest(absltest.TestCase):

  def testUnpacksKnownRdfStruct(self):
    user = rdf_client.User()
    user.username = "foo"
    payload = rdf_structs.AnyValue.Pack(user).SerializeToBytes()

    result = db_utils.ParseAndUnpackAny("User", payload)
    self.assertIsInstance(result, rdf_client.User)

  def testReturnsFallbackvalueIfRdfTypeNotKnown(self):
    user = rdf_client.User()
    user.username = "foo"
    payload = rdf_structs.AnyValue.Pack(user).SerializeToBytes()

    result = db_utils.ParseAndUnpackAny("_SomeUnknownType", payload)
    self.assertIsInstance(result, rdf_objects.SerializedValueOfUnrecognizedType)
    self.assertEqual(result.type_name, "_SomeUnknownType")
    self.assertEqual(result.value, user.SerializeToBytes())


_one_second_timestamp = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(1)

if __name__ == "__main__":
  app.run(test_lib.main)
