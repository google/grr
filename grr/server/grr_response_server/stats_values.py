#!/usr/bin/env python
"""RDF values for representing stats in the data-store."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import stats as rdf_stats
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import jobs_pb2


class StatsStoreFieldValue(rdf_structs.RDFProtoStruct):
  """RDFValue definition for fields values to be stored in the data store."""

  protobuf = jobs_pb2.StatsStoreFieldValue

  @property
  def value(self):
    if self.field_type == rdf_stats.MetricFieldDefinition.FieldType.INT:
      value = self.int_value
    elif self.field_type == rdf_stats.MetricFieldDefinition.FieldType.STR:
      value = self.str_value
    else:
      raise ValueError("Internal inconsistency, invalid "
                       "field type %d." % self.field_type)

    return value

  def SetValue(self, value, field_type):
    if field_type == rdf_stats.MetricFieldDefinition.FieldType.INT:
      self.int_value = value
    elif field_type == rdf_stats.MetricFieldDefinition.FieldType.STR:
      self.str_value = value
    else:
      raise ValueError("Invalid field type %d." % field_type)

    self.field_type = field_type


class StatsStoreValue(rdf_structs.RDFProtoStruct):
  """RDFValue definition for stats values to be stored in the data store."""
  protobuf = jobs_pb2.StatsStoreValue
  rdf_deps = [
      rdf_stats.Distribution,
      StatsStoreFieldValue,
  ]

  @property
  def value(self):
    if self.value_type == rdf_stats.MetricMetadata.ValueType.INT:
      value = self.int_value
    elif self.value_type == rdf_stats.MetricMetadata.ValueType.FLOAT:
      value = self.float_value
    elif self.value_type == rdf_stats.MetricMetadata.ValueType.STR:
      value = self.str_value
    elif self.value_type == rdf_stats.MetricMetadata.ValueType.DISTRIBUTION:
      value = self.distribution_value
    else:
      raise ValueError("Internal inconsistency, invalid "
                       "value type %d." % self.value_type)

    return value

  def SetValue(self, value, value_type):
    if value_type == rdf_stats.MetricMetadata.ValueType.INT:
      self.int_value = value
    elif value_type == rdf_stats.MetricMetadata.ValueType.FLOAT:
      self.float_value = value
    elif value_type == rdf_stats.MetricMetadata.ValueType.STR:
      self.str_value = value
    elif value_type == rdf_stats.MetricMetadata.ValueType.DISTRIBUTION:
      self.distribution_value = value
    else:
      raise ValueError("Invalid value type %d." % value_type)

    self.value_type = value_type


class StatsStoreEntry(rdf_structs.RDFProtoStruct):
  """Represents a single entry/row in the StatsEntries table."""
  protobuf = jobs_pb2.StatsStoreEntry
  rdf_deps = [
      StatsStoreValue,
      rdfvalue.RDFDatetime,
  ]
