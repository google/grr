#!/usr/bin/env python
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import itertools

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import stats as rdf_stats
from grr_response_core.stats import default_stats_collector
from grr_response_core.stats import stats_collector_instance
from grr_response_core.stats import stats_test_utils
from grr_response_core.stats import stats_utils
from grr_response_server import db
from grr_response_server import stats_values

_TEST_PROCESS_ID = "test_process"
_SINGLE_DIM_COUNTER = "single_dim_counter"
_MULTI_DIM_COUNTER = "multi_dim_counter"

# RDF protobufs used for testing.
#
# TODO(user): Refactor rel-db tests so that component-specific test-mixin
# classes do not have to worry about defining attributes/methods that conflict
# with those of other mixin classes.
_single_dim_entry1 = stats_values.StatsStoreEntry(
    process_id=_TEST_PROCESS_ID,
    metric_name=_SINGLE_DIM_COUNTER,
    metric_value=stats_values.StatsStoreValue(
        value_type=rdf_stats.MetricMetadata.ValueType.INT, int_value=42),
    timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(1))
_single_dim_entry2 = stats_values.StatsStoreEntry(
    process_id=_TEST_PROCESS_ID,
    metric_name=_SINGLE_DIM_COUNTER,
    metric_value=stats_values.StatsStoreValue(
        value_type=rdf_stats.MetricMetadata.ValueType.INT, int_value=42),
    timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(2))
_single_dim_entry3 = stats_values.StatsStoreEntry(
    process_id=_TEST_PROCESS_ID,
    metric_name=_SINGLE_DIM_COUNTER,
    metric_value=stats_values.StatsStoreValue(
        value_type=rdf_stats.MetricMetadata.ValueType.INT, int_value=42),
    timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(3))
_multi_dim_entry = stats_values.StatsStoreEntry(
    process_id=_TEST_PROCESS_ID,
    metric_name=_MULTI_DIM_COUNTER,
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
    timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(2))


class DatabaseTestStatsMixin(object):

  # TODO(user): Refactor rel-db tests so it becomes possible/natural to
  # have setUp() functions in component-specific mixins like this one.
  def _SetUpStatsTest(self):
    """Does set-up operations prior to running tests."""
    self._SetUpFakeStatsContext()

    self.db.WriteStatsStoreEntries([
        _single_dim_entry1, _single_dim_entry2, _single_dim_entry3,
        _multi_dim_entry
    ])

  def _SetUpFakeStatsContext(self):
    """Registers stats metrics used by tests in this class."""
    # DB implementations might interact with real metrics (not defined in this
    # test), so we make sure that they get registered.
    real_metrics = list(
        stats_collector_instance.Get().GetAllMetricsMetadata().values())
    test_metrics = [
        stats_utils.CreateCounterMetadata(_SINGLE_DIM_COUNTER),
        stats_utils.CreateCounterMetadata(
            _MULTI_DIM_COUNTER,
            fields=[("str_field1", str), ("str_field2", str)]),
    ]
    fake_stats_context = stats_test_utils.FakeStatsContext(
        default_stats_collector.DefaultStatsCollector(real_metrics +
                                                      test_metrics))
    fake_stats_context.start()
    self.addCleanup(fake_stats_context.stop)

  def testWriteStatsStoreEntriesValidation(self):
    self._SetUpFakeStatsContext()

    # Create StatsStoreEntries with incorrect field values.
    bad_single_dim_entry = stats_values.StatsStoreEntry()
    bad_single_dim_entry.FromDict(_multi_dim_entry.ToPrimitiveDict())
    bad_single_dim_entry.metric_name = _SINGLE_DIM_COUNTER
    bad_multi_dim_entry = stats_values.StatsStoreEntry()
    bad_multi_dim_entry.FromDict(_single_dim_entry1.ToPrimitiveDict())
    bad_multi_dim_entry.metric_name = _MULTI_DIM_COUNTER

    with self.assertRaises(ValueError) as cm:
      self.db.WriteStatsStoreEntries([bad_single_dim_entry])
    self.assertEqual(
        "Value for metric single_dim_counter had 2 field values, yet the "
        "metric was defined to have 0 fields.", cm.exception.message)

    with self.assertRaises(ValueError) as cm:
      self.db.WriteStatsStoreEntries([bad_multi_dim_entry])
    self.assertEqual(
        "Value for metric multi_dim_counter had 0 field values, yet the "
        "metric was defined to have 2 fields.", cm.exception.message)

  def testDuplicateStatsEntryWrite_SingleDimensional(self):
    """Tests errors raised when writing duplicate single-dimensional entries."""
    self._SetUpStatsTest()
    duplicate_entry = stats_values.StatsStoreEntry()
    duplicate_entry.FromDict(_single_dim_entry1.ToPrimitiveDict())
    duplicate_entry.metric_value.int_value = 43
    with self.assertRaises(db.DuplicateMetricValueError):
      self.db.WriteStatsStoreEntries([duplicate_entry])

  def testDuplicateStatsEntryWrite_MultiDimensional(self):
    """Tests errors raised when writing duplicate multi-dimensional entries."""
    self._SetUpStatsTest()
    duplicate_entry = stats_values.StatsStoreEntry()
    duplicate_entry.FromDict(_multi_dim_entry.ToPrimitiveDict())
    duplicate_entry.metric_value.int_value = 43
    with self.assertRaises(db.DuplicateMetricValueError):
      self.db.WriteStatsStoreEntries([duplicate_entry])

  def testReadAllStatsEntries_UnknownPrefix(self):
    self._SetUpStatsTest()
    read_entries = self.db.ReadStatsStoreEntries("unknown_prefix",
                                                 _SINGLE_DIM_COUNTER)
    self.assertEmpty(read_entries)

  def testReadAllStatsEntries_UnknownMetric(self):
    self._SetUpStatsTest()
    read_entries = self.db.ReadStatsStoreEntries(_TEST_PROCESS_ID,
                                                 "unknown_metric")
    self.assertEmpty(read_entries)

  def testReadAllStatsEntries_PrefixMatch(self):
    self._SetUpStatsTest()
    self._AssertSameRDFProtoElements(
        [_single_dim_entry1, _single_dim_entry2, _single_dim_entry3],
        self.db.ReadStatsStoreEntries("test_p", _SINGLE_DIM_COUNTER))

  def testReadStatsEntriesLimitMaxResults(self):
    self._SetUpStatsTest()
    read_entries = self.db.ReadStatsStoreEntries(
        _TEST_PROCESS_ID, _SINGLE_DIM_COUNTER, max_results=1)
    self.assertLen(read_entries, 1)
    self.assertEqual(read_entries[0].metric_name, _SINGLE_DIM_COUNTER)

  def testReadStatsEntriesLimitTimeRange(self):
    self._SetUpStatsTest()
    start = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(2)
    end = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(5)
    read_entries = self.db.ReadStatsStoreEntries(
        _TEST_PROCESS_ID, _SINGLE_DIM_COUNTER, time_range=(start, end))
    # Only entries in the given time range are returned.
    self._AssertSameRDFProtoElements([_single_dim_entry2, _single_dim_entry3],
                                     read_entries)

  def testDeleteStatsEntries_HighLimit(self):
    self._SetUpStatsTest()
    cutoff = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(3)
    num_deleted = self.db.DeleteStatsStoreEntriesOlderThan(cutoff, limit=100)
    single_dim_entries = self.db.ReadStatsStoreEntries(_TEST_PROCESS_ID,
                                                       _SINGLE_DIM_COUNTER)
    multi_dim_entries = self.db.ReadStatsStoreEntries(_TEST_PROCESS_ID,
                                                      _MULTI_DIM_COUNTER)
    self._AssertSameRDFProtoElements([_single_dim_entry3], single_dim_entries)
    self.assertEmpty(multi_dim_entries)
    self.assertEqual(num_deleted, 3)

  def testDeleteStatsEntries_LowLimit(self):
    self._SetUpStatsTest()
    cutoff = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(3)
    num_deleted = self.db.DeleteStatsStoreEntriesOlderThan(cutoff, limit=2)
    single_dim_entries = self.db.ReadStatsStoreEntries(_TEST_PROCESS_ID,
                                                       _SINGLE_DIM_COUNTER)
    multi_dim_entries = self.db.ReadStatsStoreEntries(_TEST_PROCESS_ID,
                                                      _MULTI_DIM_COUNTER)
    # Two entries should be deleted, leaving 2.
    self.assertLen(single_dim_entries + multi_dim_entries, 2)
    self.assertEqual(num_deleted, 2)

  def _AssertSameRDFProtoElements(self, expected_seq, actual_seq):
    """Wrapper around abseil's assertCountEqual() for RDFProtoStructs.

    This gives us more readable failure messages by converting the RDF protos
    to dicts.

    Args:
      expected_seq: Expected sequence of RDFProtoStructs.
      actual_seq: Actual sequence of RDFProtoStructs returned by the DB
        implementation.
    """
    # Make sure sure all repeated fields are initialized.
    for entry in itertools.chain(expected_seq, actual_seq):
      # This is an ugly hack get around the fact that the value of a repeated
      # RDFProto field can change after it is accessed. In particular, if before
      # it was unset, accessing the field without assigning it sets it to the
      # empty list. Even worse, this change is not apparent after converting the
      # RDF protos to raw protobufs then serializing those to strings.
      entry.metric_value.fields_values  # pylint: disable=pointless-statement

    expected_dicts = [entry.ToPrimitiveDict() for entry in expected_seq]
    actual_dicts = [entry.ToPrimitiveDict() for entry in actual_seq]
    self.assertCountEqual(expected_dicts, actual_dicts)
