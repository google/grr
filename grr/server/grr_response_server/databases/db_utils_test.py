#!/usr/bin/env python
# Lint as: python3
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import logging
from unittest import mock

from absl import app
from absl.testing import absltest

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.util import compatibility
from grr_response_server.databases import db
from grr_response_server.databases import db_utils
from grr.test_lib import stats_test_lib
from grr.test_lib import test_lib


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
        fields=[compatibility.GetName(fn)]):
      with self.assertStatsCounterDelta(
          grr_errors_count_increment,
          db_utils.DB_REQUEST_ERRORS,
          fields=[compatibility.GetName(fn), "grr"]):
        with self.assertStatsCounterDelta(
            db_errors_count_increment,
            db_utils.DB_REQUEST_ERRORS,
            fields=[compatibility.GetName(fn), "db"]):
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


_one_second_timestamp = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(1)

if __name__ == "__main__":
  app.run(test_lib.main)
