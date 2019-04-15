#!/usr/bin/env python
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import logging

from absl import app
from absl.testing import absltest
import mock

from grr_response_core.lib import rdfvalue
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
        latency_count_increment, "db_request_latency", fields=[fn.__name__]):
      with self.assertStatsCounterDelta(
          grr_errors_count_increment,
          "db_request_errors",
          fields=[fn.__name__, "grr"]):
        with self.assertStatsCounterDelta(
            db_errors_count_increment,
            "db_request_errors",
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


_one_second_timestamp = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(1)

if __name__ == "__main__":
  app.run(test_lib.main)
