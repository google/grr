#!/usr/bin/env python
import logging

from absl import app
from absl.testing import absltest

from grr_response_core.lib import rdfvalue
from grr_response_server.databases import db
from grr_response_server.databases import db_utils
from grr.test_lib import stats_test_lib
from grr.test_lib import test_lib


class TypeURLToRDFTypeNameTest(absltest.TestCase):
  """Test class for TypeURLToRDFTypeName."""

  def testReturnsCorrectValuesForWrapperTypes(self):
    self.assertEqual(
        db_utils.TypeURLToRDFTypeName(
            "type.googleapis.com/google.protobuf.BytesValue"
        ),
        "RDFBytes",
    )
    self.assertEqual(
        db_utils.TypeURLToRDFTypeName(
            "type.googleapis.com/google.protobuf.StringValue"
        ),
        "RDFString",
    )
    self.assertEqual(
        db_utils.TypeURLToRDFTypeName(
            "type.googleapis.com/google.protobuf.Int64Value"
        ),
        "RDFInteger",
    )

  def testRaisesOnUnknownWrapperTypes(self):
    with self.assertRaises(db_utils.UnsupportedWrapperTypeError):
      db_utils.TypeURLToRDFTypeName(
          "type.googleapis.com/google.protobuf.Int32Value"
      )

  def testReturnCorrectValuesForNonWrapperTypes(self):
    self.assertEqual(
        db_utils.TypeURLToRDFTypeName(
            "type.googleapis.com/grr.ClientSummary"
        ),
        "ClientSummary",
    )

  def testRaisesOnInvalidPackageNameWithGrrPrefix(self):
    with self.assertRaises(db_utils.InvalidTypeURLError):
      db_utils.TypeURLToRDFTypeName(
          "type.googleapis.com/grr.blah.ClientSummary"
      )


class RDFTypeNameToTypeURLTest(absltest.TestCase):
  """Test class for RDFTypeNameToTypeURL."""

  def testReturnsCorrectValuesForWrapperTypes(self):
    self.assertEqual(
        db_utils.RDFTypeNameToTypeURL("RDFBytes"),
        "type.googleapis.com/google.protobuf.BytesValue",
    )
    self.assertEqual(
        db_utils.RDFTypeNameToTypeURL("RDFString"),
        "type.googleapis.com/google.protobuf.StringValue",
    )
    self.assertEqual(
        db_utils.RDFTypeNameToTypeURL("RDFInteger"),
        "type.googleapis.com/google.protobuf.Int64Value",
    )

  def testReturnCorrectValuesForNonWrapperTypes(self):
    self.assertEqual(
        db_utils.RDFTypeNameToTypeURL("ClientSummary"),
        "type.googleapis.com/grr.ClientSummary",
    )


class BatchPlannerTest(absltest.TestCase):
  """Test class for OperatioBatcher."""

  def testSingleOperationLowerThanLimit(self):
    batch_planner = db_utils.BatchPlanner(10)
    batch_planner.PlanOperation("a", 9)

    self.assertEqual(
        batch_planner.batches,
        [
            [("a", 0, 9)],
        ],
    )

  def testMultipleOperationsLowerThanLimitInTotal(self):
    batch_planner = db_utils.BatchPlanner(10)
    batch_planner.PlanOperation("a", 3)
    batch_planner.PlanOperation("b", 3)
    batch_planner.PlanOperation("c", 3)

    self.assertEqual(
        batch_planner.batches,
        [
            [("a", 0, 3), ("b", 0, 3), ("c", 0, 3)],
        ],
    )

  def testSingleOperationBiggerThanLimit(self):
    batch_planner = db_utils.BatchPlanner(10)
    batch_planner.PlanOperation("a", 12)

    self.assertEqual(
        batch_planner.batches,
        [
            [("a", 0, 10)],
            [("a", 10, 2)],
        ],
    )

  def testSingleOperationMoreThanTwiceBiggerThanLimit(self):
    batch_planner = db_utils.BatchPlanner(10)
    batch_planner.PlanOperation("a", 22)

    self.assertEqual(
        batch_planner.batches,
        [
            [("a", 0, 10)],
            [("a", 10, 10)],
            [("a", 20, 2)],
        ],
    )

  def testMultipleOperationsBiggerThanLimitInTotal(self):
    batch_planner = db_utils.BatchPlanner(10)
    batch_planner.PlanOperation("a", 3)
    batch_planner.PlanOperation("b", 3)
    batch_planner.PlanOperation("c", 3)
    batch_planner.PlanOperation("d", 3)

    self.assertEqual(
        batch_planner.batches,
        [
            [("a", 0, 3), ("b", 0, 3), ("c", 0, 3), ("d", 0, 1)],
            [("d", 1, 2)],
        ],
    )

  def testMultipleOperationsTwiceBiggerThanLimitInTotal(self):
    batch_planner = db_utils.BatchPlanner(10)
    batch_planner.PlanOperation("a", 3)
    batch_planner.PlanOperation("b", 3)
    batch_planner.PlanOperation("c", 3)
    batch_planner.PlanOperation("d", 3)
    batch_planner.PlanOperation("e", 3)
    batch_planner.PlanOperation("f", 3)
    batch_planner.PlanOperation("g", 3)

    self.assertEqual(
        batch_planner.batches,
        [
            [("a", 0, 3), ("b", 0, 3), ("c", 0, 3), ("d", 0, 1)],
            [("d", 1, 2), ("e", 0, 3), ("f", 0, 3), ("g", 0, 2)],
            [("g", 2, 1)],
        ],
    )

  def testMultipleOperationsEachBiggerThanLimit(self):
    batch_planner = db_utils.BatchPlanner(10)
    batch_planner.PlanOperation("a", 12)
    batch_planner.PlanOperation("b", 12)

    self.assertEqual(
        batch_planner.batches,
        [
            [("a", 0, 10)],
            [("a", 10, 2), ("b", 0, 8)],
            [("b", 8, 4)],
        ],
    )


class CallAccountedTest(stats_test_lib.StatsTestMixin, absltest.TestCase):

  @db_utils.CallAccounted
  def SampleCall(self):
    return 42

  @db_utils.CallAccounted
  def SampleCallWithGRRError(self):
    raise db.UnknownGRRUserError("Unknown")

  @db_utils.CallAccounted
  def SampleCallWithDBError(self):
    raise RuntimeError("some")

  def testReturnValueIsPropagated(self):
    self.assertEqual(self.SampleCall(), 42)

  def _ExpectIncrements(
      self,
      fn,
      latency_count_increment,
      grr_errors_count_increment,
      db_errors_count_increment,
  ):

    with self.assertStatsCounterDelta(
        latency_count_increment,
        db_utils.DB_REQUEST_LATENCY,
        fields=[fn.__name__],
    ):
      with self.assertStatsCounterDelta(
          grr_errors_count_increment,
          db_utils.DB_REQUEST_ERRORS,
          fields=[fn.__name__, "grr"],
      ):
        with self.assertStatsCounterDelta(
            db_errors_count_increment,
            db_utils.DB_REQUEST_ERRORS,
            fields=[fn.__name__, "db"],
        ):
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


class CallLoggedTest(absltest.TestCase):

  def setUp(self):
    super().setUp()

    logger = logging.getLogger()

    class Handler(logging.Handler):

      def __init__(self):
        super().__init__()
        self.logs: list[logging.LogRecord] = []

      def emit(self, record: logging.LogRecord):
        self.logs.append(record)

    # We create our own log handler that stores all records in a simple list.
    self.handler = Handler()
    logger.addHandler(self.handler)
    self.addCleanup(lambda: logger.removeHandler(self.handler))

    # We adjust log level to `DEBUG` to catch all logs.
    old_log_level = logger.level
    logger.setLevel(logging.DEBUG)
    self.addCleanup(lambda: logger.setLevel(old_log_level))

    # We also need to make sure logging hasn't been disabled.
    old_log_level_override = logger.manager.disable
    logging.disable(logging.NOTSET)
    self.addCleanup(lambda: logging.disable(old_log_level_override))

  def testArgsAndResultPropagated(self):
    @db_utils.CallLogged
    def SampleCall(arg: int, kwarg: int = 0) -> tuple[int, int]:
      return (arg, kwarg)

    self.assertEqual(SampleCall(42, 1337), (42, 1337))

  def testCallSuccessLogged(self):
    @db_utils.CallLogged
    def SampleCall():
      return 42

    SampleCall()

    self.assertLen(self.handler.logs, 1)

    message = self.handler.logs[0].getMessage()
    self.assertIn("SUCCESS", message)
    self.assertIn("SampleCall", message)

  def testCallRaisedDBErrorLogged(self):
    @db_utils.CallLogged
    def SampleCallWithDBError():
      raise db.UnknownGRRUserError("Unknown")

    with self.assertRaises(db.UnknownGRRUserError):
      SampleCallWithDBError()

    self.assertLen(self.handler.logs, 1)

    message = self.handler.logs[0].getMessage()
    self.assertIn("GRR ERROR", message)
    self.assertIn("SampleCallWithDBError", message)

  def testCallRaisedGenericErrorLogged(self):
    @db_utils.CallLogged
    def SampleCallWithGenericError():
      raise RuntimeError()

    with self.assertRaises(RuntimeError):
      SampleCallWithGenericError()

    self.assertLen(self.handler.logs, 1)

    message = self.handler.logs[0].getMessage()
    self.assertIn("INTERNAL DB ERROR", message)
    self.assertIn("SampleCallWithGenericError", message)


class IdToIntConversionTest(absltest.TestCase):

  def testFlowIdToInt(self):
    self.assertEqual(db_utils.FlowIDToInt("00000001"), 1)
    self.assertEqual(db_utils.FlowIDToInt("1234ABCD"), 0x1234ABCD)
    self.assertEqual(db_utils.FlowIDToInt("FFFFFFFF"), 0xFFFFFFFF)
    self.assertEqual(db_utils.FlowIDToInt("0000000100000000"), 0x100000000)
    self.assertEqual(
        db_utils.FlowIDToInt("FFFFFFFFFFFFFFFF"), 0xFFFFFFFFFFFFFFFF
    )

  def testIntToFlowId(self):
    self.assertEqual(db_utils.IntToFlowID(1), "00000001")
    self.assertEqual(db_utils.IntToFlowID(0x1234ABCD), "1234ABCD")
    self.assertEqual(db_utils.IntToFlowID(0xFFFFFFFF), "FFFFFFFF")
    self.assertEqual(db_utils.IntToFlowID(0x100000000), "0000000100000000")
    self.assertEqual(
        db_utils.IntToFlowID(0xFFFFFFFFFFFFFFFF), "FFFFFFFFFFFFFFFF"
    )

  def testHuntIdToInt(self):
    self.assertEqual(db_utils.HuntIDToInt("00000001"), 1)
    self.assertEqual(db_utils.HuntIDToInt("1234ABCD"), 0x1234ABCD)
    self.assertEqual(db_utils.HuntIDToInt("FFFFFFFF"), 0xFFFFFFFF)
    self.assertEqual(db_utils.HuntIDToInt("0000000100000000"), 0x100000000)
    self.assertEqual(
        db_utils.HuntIDToInt("FFFFFFFFFFFFFFFF"), 0xFFFFFFFFFFFFFFFF
    )

  def testIntToHuntId(self):
    self.assertEqual(db_utils.IntToHuntID(1), "00000001")
    self.assertEqual(db_utils.IntToHuntID(0x1234ABCD), "1234ABCD")
    self.assertEqual(db_utils.IntToHuntID(0xFFFFFFFF), "FFFFFFFF")
    self.assertEqual(db_utils.IntToHuntID(0x100000000), "0000000100000000")
    self.assertEqual(
        db_utils.IntToHuntID(0xFFFFFFFFFFFFFFFF), "FFFFFFFFFFFFFFFF"
    )


_one_second_timestamp = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(1)

if __name__ == "__main__":
  app.run(test_lib.main)
