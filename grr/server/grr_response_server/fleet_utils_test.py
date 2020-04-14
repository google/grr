#!/usr/bin/env python
# Lint as: python3
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from absl.testing import absltest

from grr_response_server import fleet_utils


def _BuildTestStats():
  builder = fleet_utils.FleetStatsBuilder({1, 5, 10})
  builder.IncrementLabel("foo-label", "category-foo", 1)
  builder.IncrementLabel("foo-label", "category-foo", 1, delta=4)
  builder.IncrementLabel("foo-label", "category-foo", 5, delta=5)
  builder.IncrementLabel("foo-label", "category-foo", 10, delta=5)
  builder.IncrementLabel("bar-label", "category-foo", 5)
  builder.IncrementLabel("bar-label", "category-foo", 10)
  builder.IncrementLabel("bar-label", "category-bar", 5)
  builder.IncrementLabel("bar-label", "category-bar", 10)

  builder.IncrementTotal("category-foo", 1)
  builder.IncrementTotal("category-foo", 1, delta=6)
  builder.IncrementTotal("category-foo", 5, delta=7)
  builder.IncrementTotal("category-foo", 10, delta=7)
  builder.IncrementTotal("category-bar", 5, delta=3)
  builder.IncrementTotal("category-bar", 10, delta=3)
  return builder.Build()


class FleetStatsTest(absltest.TestCase):

  def testBuildWithInvalidBucket(self):
    builder = fleet_utils.FleetStatsBuilder({1, 5, 10})
    expected_exception = "Invalid bucket '3'. Allowed buckets are [1, 5, 10]."
    with self.assertRaisesWithLiteralMatch(ValueError, expected_exception):
      builder.IncrementLabel("foo-label", "category-foo", 3)
    with self.assertRaisesWithLiteralMatch(ValueError, expected_exception):
      builder.IncrementTotal("category-foo", 3)

  def testBuildWithInvalidData(self):
    builder = fleet_utils.FleetStatsBuilder({1, 5, 10})
    builder.IncrementLabel("foo-label", "category-foo", 1, delta=6)
    expected_exception = ("Day-bucket counts for label foo-label are invalid: "
                          "[(1, 6), (5, 0), (10, 0)].")
    with self.assertRaisesWithLiteralMatch(ValueError, expected_exception):
      builder.Build()
    builder.IncrementLabel("foo-label", "category-foo", 5, delta=6)
    builder.IncrementLabel("foo-label", "category-foo", 10, delta=7)
    builder.IncrementTotal("category-foo", 5)
    expected_exception = (
        "Day-bucket counts for fleet-wide totals are invalid: "
        "[(1, 0), (5, 1), (10, 0)].")
    with self.assertRaisesWithLiteralMatch(ValueError, expected_exception):
      builder.Build()

  def testGetAllLabelsAndBuckets(self):
    fleet_stats = _BuildTestStats()
    self.assertListEqual(fleet_stats.GetAllLabels(), ["bar-label", "foo-label"])
    self.assertListEqual(fleet_stats.GetDayBuckets(), [1, 5, 10])

  def testGetValuesForDayAndLabel(self):
    fleet_stats = _BuildTestStats()
    self.assertDictEqual(
        fleet_stats.GetValuesForDayAndLabel(1, "foo-label"),
        {"category-foo": 5})
    self.assertEmpty(fleet_stats.GetValuesForDayAndLabel(1, "bar-label"))
    self.assertDictEqual(
        fleet_stats.GetValuesForDayAndLabel(5, "foo-label"),
        {"category-foo": 5})
    self.assertDictEqual(
        fleet_stats.GetValuesForDayAndLabel(5, "bar-label"), {
            "category-bar": 1,
            "category-foo": 1,
        })
    self.assertDictEqual(
        fleet_stats.GetValuesForDayAndLabel(10, "bar-label"), {
            "category-bar": 1,
            "category-foo": 1,
        })
    self.assertEmpty(fleet_stats.GetValuesForDayAndLabel(1, "unknown-label"))

  def testGetValuesForDayAndLabel_InvalidBucket(self):
    fleet_stats = _BuildTestStats()
    expected_exception = "Invalid bucket '3'. Allowed buckets are [1, 5, 10]."
    with self.assertRaisesWithLiteralMatch(ValueError, expected_exception):
      fleet_stats.GetValuesForDayAndLabel(3, "foo-label")

  def testGetTotalsForDay(self):
    fleet_stats = _BuildTestStats()
    self.assertDictEqual(fleet_stats.GetTotalsForDay(1), {"category-foo": 7})
    self.assertDictEqual(
        fleet_stats.GetTotalsForDay(5), {
            "category-bar": 3,
            "category-foo": 7,
        })
    self.assertDictEqual(
        fleet_stats.GetTotalsForDay(10), {
            "category-bar": 3,
            "category-foo": 7,
        })

  def testGetTotalsForDay_InvalidBucket(self):
    fleet_stats = _BuildTestStats()
    expected_exception = "Invalid bucket '3'. Allowed buckets are [1, 5, 10]."
    with self.assertRaisesWithLiteralMatch(ValueError, expected_exception):
      fleet_stats.GetTotalsForDay(3)

  def testFlattenLabelCounts(self):
    fleet_stats = _BuildTestStats()
    self.assertDictEqual(
        fleet_stats.GetFlattenedLabelCounts(), {
            (1, "foo-label", "category-foo"): 5,
            (5, "foo-label", "category-foo"): 5,
            (10, "foo-label", "category-foo"): 5,
            (5, "bar-label", "category-foo"): 1,
            (10, "bar-label", "category-foo"): 1,
            (5, "bar-label", "category-bar"): 1,
            (10, "bar-label", "category-bar"): 1,
        })

  def testFlattenTotalCounts(self):
    fleet_stats = _BuildTestStats()
    self.assertDictEqual(
        fleet_stats.GetFlattenedTotalCounts(), {
            (1, "category-foo"): 7,
            (5, "category-foo"): 7,
            (10, "category-foo"): 7,
            (5, "category-bar"): 3,
            (10, "category-bar"): 3,
        })

  def testGetAggregatedLabelCounts(self):
    fleet_stats = _BuildTestStats()
    self.assertDictEqual(fleet_stats.GetAggregatedLabelCounts(), {
        "foo-label": {
            1: 5,
            5: 5,
            10: 5,
        },
        "bar-label": {
            1: 0,
            5: 2,
            10: 2,
        },
    })

  def testGetAggregatedTotalCounts(self):
    fleet_stats = _BuildTestStats()
    self.assertDictEqual(fleet_stats.GetAggregatedTotalCounts(), {
        1: 7,
        5: 10,
        10: 10,
    })


if __name__ == "__main__":
  absltest.main()
