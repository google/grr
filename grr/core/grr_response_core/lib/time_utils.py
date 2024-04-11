#!/usr/bin/env python
"""Time-related utilities."""

from grr_response_core.lib import rdfvalue


class TimeRange:
  """An object representing a closed time-range.

  Attributes:
    start: An RDFDatetime that indicates the beginning of the time-range.
    end: An RDFDatetime that indicates the end of the time-range.
  """

  def __init__(self, start: rdfvalue.RDFDatetime, end: rdfvalue.RDFDatetime):
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
          "Invalid time-range: %s > %s."
          % (start.AsMicrosecondsSinceEpoch(), end.AsMicrosecondsSinceEpoch())
      )
    self._start = start
    self._end = end

  @property
  def start(self):
    return self._start

  @property
  def end(self):
    return self._end

  def Includes(self, timestamp: rdfvalue.RDFDatetime) -> bool:
    """Returns true iff the given timestamp is included in the TimeRange."""
    return self._start <= timestamp <= self._end
