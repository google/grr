#!/usr/bin/env python
"""Operations on a series of points, indexed by time.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import copy

from builtins import range  # pylint: disable=redefined-builtin

from grr_response_core.lib import rdfvalue

NORMALIZE_MODE_GAUGE = 1
NORMALIZE_MODE_COUNTER = 2


class Timeseries(object):
  """Timeseries contains a sequence of points, each with a timestamp."""

  def __init__(self, initializer=None):
    """Create a timeseries with an optional initializer.

    Args:
      initializer: An optional Timeseries to clone.

    Raises:
      RuntimeError: If initializer is not understood.
    """
    if initializer is None:
      self.data = []
      return
    if isinstance(initializer, Timeseries):
      self.data = copy.deepcopy(initializer.data)
      return
    raise RuntimeError("Unrecognized initializer.")

  def _NormalizeTime(self, time):
    """Normalize a time to be an int measured in microseconds."""
    if isinstance(time, rdfvalue.RDFDatetime):
      return time.AsMicrosecondsSinceEpoch()
    if isinstance(time, rdfvalue.Duration):
      return time.microseconds
    return int(time)

  def Append(self, value, timestamp):
    """Adds value at timestamp.

    Values must be added in order of increasing timestamp.

    Args:
      value: An observed value.
      timestamp: The timestamp at which value was observed.

    Raises:
      RuntimeError: If timestamp is smaller than the previous timstamp.
    """

    timestamp = self._NormalizeTime(timestamp)
    if self.data and timestamp < self.data[-1][1]:
      raise RuntimeError("Next timestamp must be larger.")
    self.data.append([value, timestamp])

  def MultiAppend(self, value_timestamp_pairs):
    """Adds multiple value<->timestamp pairs.

    Args:
      value_timestamp_pairs: Tuples of (value, timestamp).
    """
    for value, timestamp in value_timestamp_pairs:
      self.Append(value, timestamp)

  def FilterRange(self, start_time=None, stop_time=None):
    """Filter the series to lie between start_time and stop_time.

    Removes all values of the series which are outside of some time range.

    Args:
      start_time: If set, timestamps before start_time will be dropped.
      stop_time: If set, timestamps at or past stop_time will be dropped.
    """

    start_time = self._NormalizeTime(start_time)
    stop_time = self._NormalizeTime(stop_time)
    self.data = [
        p for p in self.data
        if (start_time is None or p[1] >= start_time) and
        (stop_time is None or p[1] < stop_time)
    ]

  def Normalize(self, period, start_time, stop_time, mode=NORMALIZE_MODE_GAUGE):
    """Normalize the series to have a fixed period over a fixed time range.

    Supports two modes, depending on the type of data:

      NORMALIZE_MODE_GAUGE: support gauge values. If multiple original data
        points lie within an output interval, the output value is an average of
        the original data point.  if no original data points lie within an
        output interval, the output value is None.

      NORMALIZE_MODE_COUNTER: supports counter values. Assumes that the sequence
        is already increasing (typically, MakeIncreasing will have been
        called). Each output value is the largest value seen during or before
        the corresponding output interval.

    Args:

      period: The desired time between points. Should be an rdfvalue.Duration or
        a count of microseconds.

      start_time: The first timestamp will be at start_time. Should be an
        rdfvalue.RDFDatetime or a count of microseconds since epoch.

      stop_time: The last timestamp will be at stop_time - period. Should be an
        rdfvalue.RDFDatetime or a count of microseconds since epoch.

      mode: The type of normalization to perform. May be NORMALIZE_MODE_GAUGE or
        NORMALIZE_MODE_COUNTER.

    Raises:
      RuntimeError: In case the sequence timestamps are misordered.

    """
    period = self._NormalizeTime(period)
    start_time = self._NormalizeTime(start_time)
    stop_time = self._NormalizeTime(stop_time)
    if not self.data:
      return

    self.FilterRange(start_time, stop_time)

    grouped = {}
    for value, timestamp in self.data:
      offset = timestamp - start_time
      shifted_offset = offset - (offset % period)
      grouped.setdefault(shifted_offset, []).append(value)

    self.data = []
    last_value = None
    for offset in range(0, stop_time - start_time, period):
      g = grouped.get(offset)
      if mode == NORMALIZE_MODE_GAUGE:
        v = None
        if g:
          v = sum(g) / len(g)
        self.data.append([v, offset + start_time])
      else:
        if g:
          for v in g:
            if v < last_value:
              raise RuntimeError("Next value must not be smaller.")
            last_value = v
        self.data.append([last_value, offset + start_time])

  def MakeIncreasing(self):
    """Makes the time series increasing.

    Assumes that series is based on a counter which is occasionally reset, and
    using this assumption converts the sequence to estimate the total number of
    counts which occurred.

    NOTE: Could give inacurate numbers in either of the following cases: 1)
    Multiple resets occur between samples. 2) A reset is followed by a spike
    larger than the previous level.

    """
    offset = 0
    last_value = None
    for p in self.data:
      if last_value and last_value > p[0]:
        # Assume that it was only reset once.
        offset += last_value
      last_value = p[0]
      if offset:
        p[0] += offset

  def ToDeltas(self):
    """Convert the sequence to the sequence of differences between points.

    The value of each point v[i] is replaced by v[i+1] - v[i], except for the
    last point which is dropped.
    """
    if len(self.data) < 2:
      self.data = []
      return
    for i in range(0, len(self.data) - 1):
      if self.data[i][0] is None or self.data[i + 1][0] is None:
        self.data[i][0] = None
      else:
        self.data[i][0] = self.data[i + 1][0] - self.data[i][0]
    del self.data[-1]

  def Add(self, other):
    """Add other to self pointwise.

    Requires that both self and other are of the same length, and contain
    identical timestamps. Typically this means that Normalize has been called
    on both with identical time parameters.

    Args:
      other: The sequence to add to self.

    Raises:
      RuntimeError: other does not contain the same timestamps as self.
    """
    if len(self.data) != len(other.data):
      raise RuntimeError("Can only add series of identical lengths.")
    for i in range(len(self.data)):
      if self.data[i][1] != other.data[i][1]:
        raise RuntimeError("Timestamp mismatch.")
      if self.data[i][0] is None and other.data[i][0] is None:
        continue
      self.data[i][0] = (self.data[i][0] or 0) + (other.data[i][0] or 0)

  def Rescale(self, multiplier):
    """Multiply pointwise by multiplier."""
    for p in self.data:
      if p[0] is not None:
        p[0] *= multiplier

  def Mean(self):
    """Return the arithmatic mean of all values."""
    values = [v for v, _ in self.data if v is not None]
    if not values:
      return None

    # TODO(hanuszczak): Why do we return a floored division result instead of
    # the exact value?
    return sum(values) // len(values)
