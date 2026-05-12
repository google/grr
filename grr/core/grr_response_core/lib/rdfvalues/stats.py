#!/usr/bin/env python
"""RDFValue instances related to the statistics collection."""

import bisect

from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import jobs_pb2


class Distribution(rdf_structs.RDFProtoStruct):
  """Statistics values for events - i.e. things that take time."""

  protobuf = jobs_pb2.Distribution

  def __init__(self, initializer=None, bins=None):
    if initializer and bins:
      raise ValueError(
          "Either 'initializer' or 'bins' arguments can be specified."
      )

    super().__init__(initializer=initializer)

    if bins:
      self.bins = [-float("inf")] + bins
    else:
      self.bins = []

    self.heights = [0] * len(self.bins)

  def Record(self, value):
    """Records given value."""
    self.sum += value
    self.count += 1

    pos = bisect.bisect(self.bins, value) - 1
    if pos < 0:
      pos = 0
    elif pos == len(self.bins):
      pos = len(self.bins) - 1

    self.heights[pos] += 1

  @property
  def bins_heights(self):
    return dict(zip(self.bins, self.heights))


class MetricFieldDefinition(rdf_structs.RDFProtoStruct):
  """Metric field definition."""

  protobuf = jobs_pb2.MetricFieldDefinition


class MetricMetadata(rdf_structs.RDFProtoStruct):
  """Metric metadata for a particular metric."""

  protobuf = jobs_pb2.MetricMetadata
  rdf_deps = [
      MetricFieldDefinition,
  ]

  def DefaultValue(self):
    if self.value_type == self.ValueType.INT:
      return 0
    elif self.value_type == self.ValueType.FLOAT:
      return 0.0
    elif self.value_type == self.ValueType.DISTRIBUTION:
      return Distribution()
    else:
      raise ValueError("Illegal value type: {!r}".format(self.value_type))

