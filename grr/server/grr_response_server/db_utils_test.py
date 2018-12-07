#!/usr/bin/env python
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import logging

from absl.testing import absltest
import mock

from grr_response_core.lib import flags
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import stats as rdf_stats
from grr_response_server import db
from grr_response_server import db_utils
from grr_response_server import stats_values
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


class StatsDBUtilsTest(absltest.TestCase):

  def testStatsEntryId_VaryStringDimensions(self):
    """Ensures StatsEntries with different str dimensions get different ids."""
    entry1 = stats_values.StatsStoreEntry(
        process_id="test_process",
        metric_name="test_metric",
        metric_value=stats_values.StatsStoreValue(
            value_type=rdf_stats.MetricMetadata.ValueType.INT,
            fields_values=[
                stats_values.StatsStoreFieldValue(
                    field_type=rdf_stats.MetricFieldDefinition.FieldType.STR,
                    str_value="dim1"),
                stats_values.StatsStoreFieldValue(
                    field_type=rdf_stats.MetricFieldDefinition.FieldType.STR,
                    str_value="dim2")
            ],
            int_value=42),
        timestamp=_one_second_timestamp)

    # Clone entry1 and change a single dimension value.
    entry2 = stats_values.StatsStoreEntry()
    entry2.FromDict(entry1.ToPrimitiveDict())
    entry2.metric_value.fields_values[0].str_value = "dim3"

    self.assertEqual(
        db_utils.GenerateStatsEntryId(entry1),
        b"\xb8'\x1cv\xf9`\x90\xd1\x9d#{\x8a'y\xd8E\x0bx\x1b6f\xe6\x8d\x16\xb95"
        b"\x0011uy\xf9")
    self.assertEqual(
        db_utils.GenerateStatsEntryId(entry2),
        b"\xa4\xcb\x95*\xe4\x8aclM&@\xde\xba\x17\xec\x02\xc6i\xea\xc0\x1a{bQ"
        b"\xabr~w}Z\xb9\x99")

  def testStatsEntryId_VaryIntDimensions(self):
    """Ensures StatsEntries with different int dimensions get different ids."""
    entry1 = stats_values.StatsStoreEntry(
        process_id="test_process",
        metric_name="test_metric",
        metric_value=stats_values.StatsStoreValue(
            value_type=rdf_stats.MetricMetadata.ValueType.INT,
            fields_values=[
                stats_values.StatsStoreFieldValue(
                    field_type=rdf_stats.MetricFieldDefinition.FieldType.INT,
                    int_value=11),
                stats_values.StatsStoreFieldValue(
                    field_type=rdf_stats.MetricFieldDefinition.FieldType.INT,
                    int_value=12)
            ],
            int_value=42),
        timestamp=_one_second_timestamp)

    # Clone entry1 and change a single dimension value.
    entry2 = stats_values.StatsStoreEntry()
    entry2.FromDict(entry1.ToPrimitiveDict())
    entry2.metric_value.fields_values[0].int_value = 13

    self.assertEqual(
        db_utils.GenerateStatsEntryId(entry1),
        b"pl\xc31\x1a\xf8\xd5\xfe\xe1\xc6\x10gR\x10f\x0c\xb8\xd3\x96_\xa3`\x19"
        b"\xf2\x15\xc5\xa0\x8d\xbbu\xf1&")
    self.assertEqual(
        db_utils.GenerateStatsEntryId(entry2),
        b"L \x1d+\xd5<g\\\xa8\xa4\x97\xdd\xe8^\x88\xac\xc7\xbej\xae\xff\xd5S"
        b"\x10\xce\xec\x82a\xe5_\xe1\x1c")

  def testStatsEntryId_IgnoreMetricValues(self):
    """Ensures metric values have no influence id generation."""
    int_entry = stats_values.StatsStoreEntry(
        process_id="test_process",
        metric_name="test_metric",
        metric_value=stats_values.StatsStoreValue(
            value_type=rdf_stats.MetricMetadata.ValueType.INT, int_value=42),
        timestamp=_one_second_timestamp)
    float_entry = stats_values.StatsStoreEntry(
        process_id="test_process",
        metric_name="test_metric",
        metric_value=stats_values.StatsStoreValue(
            value_type=rdf_stats.MetricMetadata.ValueType.FLOAT,
            float_value=4.2),
        timestamp=_one_second_timestamp)
    str_entry = stats_values.StatsStoreEntry(
        process_id="test_process",
        metric_name="test_metric",
        metric_value=stats_values.StatsStoreValue(
            value_type=rdf_stats.MetricMetadata.ValueType.STR, str_value="foo"),
        timestamp=_one_second_timestamp)
    distribution_entry = stats_values.StatsStoreEntry(
        process_id="test_process",
        metric_name="test_metric",
        metric_value=stats_values.StatsStoreValue(
            value_type=rdf_stats.MetricMetadata.ValueType.DISTRIBUTION,
            distribution_value=rdf_stats.Distribution()),
        timestamp=_one_second_timestamp)

    expected_id = (
        b"\x8e\xf4\xe7\xdb\x03\x01}sB\x97\x98\x957\x18\x02U\xb0\xe6x\x9f"
        b"\x97Xfs/C\xedT\xd3\x89N\xe5")
    self.assertEqual(db_utils.GenerateStatsEntryId(int_entry), expected_id)
    self.assertEqual(db_utils.GenerateStatsEntryId(float_entry), expected_id)
    self.assertEqual(db_utils.GenerateStatsEntryId(str_entry), expected_id)
    self.assertEqual(
        db_utils.GenerateStatsEntryId(distribution_entry), expected_id)


if __name__ == "__main__":
  flags.StartMain(test_lib.main)
