#!/usr/bin/env python
"""RDFValue implementations for structured searches.

This module contains the RDFValue implementations for structured searches
"""

from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto.api import search_pb2


class OSCondition(rdf_structs.RDFProtoStruct):
  protobuf = search_pb2.OSCondition
  rdf_deps = []


class ConditionExpression(rdf_structs.RDFProtoStruct):
  protobuf = search_pb2.ConditionExpression
  rdf_deps = [OSCondition]


class NotExpression(rdf_structs.RDFProtoStruct):
  protobuf = search_pb2.NotExpression
  # Circular dependency
  rdf_deps = ["SearchExpression"]


class AndExpression(rdf_structs.RDFProtoStruct):
  protobuf = search_pb2.AndExpression
  # Circular dependency
  rdf_deps = ["SearchExpression"]


class OrExpression(rdf_structs.RDFProtoStruct):
  protobuf = search_pb2.OrExpression
  # Circular dependency
  rdf_deps = ["SearchExpression"]


class SearchExpression(rdf_structs.RDFProtoStruct):
  protobuf = search_pb2.SearchExpression
  rdf_deps = [NotExpression, AndExpression, OrExpression, ConditionExpression]


class SortOrder(rdf_structs.RDFProtoStruct):
  protobuf = search_pb2.SortOrder
