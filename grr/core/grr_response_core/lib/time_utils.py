#!/usr/bin/env python
"""Time-related utilities."""
from __future__ import absolute_import
from __future__ import division

from __future__ import unicode_literals

from grr_response_core.lib import rdfvalue


class TimeRange(object):
  """An object representing a closed time-range.

  Attributes:
    start: An RDFDatetime that indicates the beginning of the time-range.
    end: An RDFDatetime that indicates the end of the time-range.
  """

  def __init__(self, start, end):
    """Initializes a TimeRange.

    Args:
      start: An RDFDatetime that indicates the beginning of the time-range.
      end: An RDFDatetime that indicates the end of the time-range.

    Raises:
      ValueError: If the beginning of the time range is at a future time as
        compared to the end of the time-range.
    """
    if start > end:
      raise ValueError(
          "Invalid time-range: %s > %s." % (start.AsMicrosecondsSinceEpoch(),
                                            end.AsMicrosecondsSinceEpoch()))
    self._start = start
    self._end = end

  @property
  def start(self):
    return self._start

  @property
  def end(self):
    return self._end

  def Includes(self, timestamp):
    """Returns true iff the given timestamp is included in the TimeRange."""
    return self._start <= timestamp <= self._end
