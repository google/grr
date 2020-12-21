#!/usr/bin/env python
"""A module with the database time test mixin."""


class DatabaseTimeTestMixin(object):
  """A mixin for testing time-related methods of database implementations."""

  def testNowPositive(self):
    timestamp = self.db.Now()
    self.assertGreaterEqual(timestamp, 0)

  def testNowMonotnic(self):
    timestamp_1 = self.db.Now()
    timestamp_2 = self.db.Now()
    timestamp_3 = self.db.Now()

    self.assertLessEqual(timestamp_1, timestamp_2)
    self.assertLessEqual(timestamp_2, timestamp_3)


# This is just a mixin file and does not require a `__main__` entry.
