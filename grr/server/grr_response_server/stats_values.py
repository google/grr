#!/usr/bin/env python
"""RDF values for representing stats in the data-store."""


from grr.lib import stats
from grr.lib.rdfvalues import structs
from grr_response_proto import jobs_pb2


class StatsStoreFieldValue(structs.RDFProtoStruct):
  """RDFValue definition for fields values to be stored in the data store."""

  protobuf = jobs_pb2.StatsStoreFieldValue

  @property
  def value(self):
    if self.field_type == stats.MetricFieldDefinition.FieldType.INT:
      value = self.int_value
    elif self.field_type == stats.MetricFieldDefinition.FieldType.STR:
      value = self.str_value
    else:
      raise ValueError("Internal inconsistency, invalid "
                       "field type %d." % self.field_type)

    return value

  def SetValue(self, value, field_type):
    if field_type == stats.MetricFieldDefinition.FieldType.INT:
      self.int_value = value
    elif field_type == stats.MetricFieldDefinition.FieldType.STR:
      self.str_value = value
    else:
      raise ValueError("Invalid field type %d." % field_type)

    self.field_type = field_type


class StatsStoreValue(structs.RDFProtoStruct):
  """RDFValue definition for stats values to be stored in the data store."""
  protobuf = jobs_pb2.StatsStoreValue
  rdf_deps = [
      stats.Distribution,
      StatsStoreFieldValue,
  ]

  @property
  def value(self):
    if self.value_type == stats.MetricMetadata.ValueType.INT:
      value = self.int_value
    elif self.value_type == stats.MetricMetadata.ValueType.FLOAT:
      value = self.float_value
    elif self.value_type == stats.MetricMetadata.ValueType.STR:
      value = self.str_value
    elif self.value_type == stats.MetricMetadata.ValueType.DISTRIBUTION:
      value = self.distribution_value
    else:
      raise ValueError("Internal inconsistency, invalid "
                       "value type %d." % self.value_type)

    return value

  def SetValue(self, value, value_type):
    if value_type == stats.MetricMetadata.ValueType.INT:
      self.int_value = value
    elif value_type == stats.MetricMetadata.ValueType.FLOAT:
      self.float_value = value
    elif value_type == stats.MetricMetadata.ValueType.STR:
      self.str_value = value
    elif value_type == stats.MetricMetadata.ValueType.DISTRIBUTION:
      self.distribution_value = value
    else:
      raise ValueError("Invalid value type %d." % value_type)

    self.value_type = value_type


class StatsStoreMetricsMetadata(structs.RDFProtoStruct):
  """Container with metadata for all the metrics in a given process."""

  protobuf = jobs_pb2.StatsStoreMetricsMetadata
  rdf_deps = [
      stats.MetricMetadata,
  ]

  def AsDict(self):
    result = {}
    for metric in self.metrics:
      result[metric.varname] = metric

    return result
