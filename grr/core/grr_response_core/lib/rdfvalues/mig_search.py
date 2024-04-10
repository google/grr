#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_core.lib.rdfvalues import search as rdf_search
from grr_response_proto.api import search_pb2


def ToProtoOSCondition(rdf: rdf_search.OSCondition) -> search_pb2.OSCondition:
  return rdf.AsPrimitiveProto()


def ToRDFOSCondition(proto: search_pb2.OSCondition) -> rdf_search.OSCondition:
  return rdf_search.OSCondition.FromSerializedBytes(proto.SerializeToString())


def ToProtoConditionExpression(
    rdf: rdf_search.ConditionExpression,
) -> search_pb2.ConditionExpression:
  return rdf.AsPrimitiveProto()


def ToRDFConditionExpression(
    proto: search_pb2.ConditionExpression,
) -> rdf_search.ConditionExpression:
  return rdf_search.ConditionExpression.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoNotExpression(
    rdf: rdf_search.NotExpression,
) -> search_pb2.NotExpression:
  return rdf.AsPrimitiveProto()


def ToRDFNotExpression(
    proto: search_pb2.NotExpression,
) -> rdf_search.NotExpression:
  return rdf_search.NotExpression.FromSerializedBytes(proto.SerializeToString())


def ToProtoAndExpression(
    rdf: rdf_search.AndExpression,
) -> search_pb2.AndExpression:
  return rdf.AsPrimitiveProto()


def ToRDFAndExpression(
    proto: search_pb2.AndExpression,
) -> rdf_search.AndExpression:
  return rdf_search.AndExpression.FromSerializedBytes(proto.SerializeToString())


def ToProtoOrExpression(
    rdf: rdf_search.OrExpression,
) -> search_pb2.OrExpression:
  return rdf.AsPrimitiveProto()


def ToRDFOrExpression(
    proto: search_pb2.OrExpression,
) -> rdf_search.OrExpression:
  return rdf_search.OrExpression.FromSerializedBytes(proto.SerializeToString())


def ToProtoSearchExpression(
    rdf: rdf_search.SearchExpression,
) -> search_pb2.SearchExpression:
  return rdf.AsPrimitiveProto()


def ToRDFSearchExpression(
    proto: search_pb2.SearchExpression,
) -> rdf_search.SearchExpression:
  return rdf_search.SearchExpression.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoSortOrder(rdf: rdf_search.SortOrder) -> search_pb2.SortOrder:
  return rdf.AsPrimitiveProto()


def ToRDFSortOrder(proto: search_pb2.SortOrder) -> rdf_search.SortOrder:
  return rdf_search.SortOrder.FromSerializedBytes(proto.SerializeToString())
