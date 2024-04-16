#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2


def ToProtoPathSpec(rdf: rdf_paths.PathSpec) -> jobs_pb2.PathSpec:
  return rdf.AsPrimitiveProto()


def ToRDFPathSpec(proto: jobs_pb2.PathSpec) -> rdf_paths.PathSpec:
  return rdf_paths.PathSpec.FromSerializedBytes(proto.SerializeToString())


def ToProtoGlobComponentExplanation(
    rdf: rdf_paths.GlobComponentExplanation,
) -> flows_pb2.GlobComponentExplanation:
  return rdf.AsPrimitiveProto()


def ToRDFGlobComponentExplanation(
    proto: flows_pb2.GlobComponentExplanation,
) -> rdf_paths.GlobComponentExplanation:
  return rdf_paths.GlobComponentExplanation.FromSerializedBytes(
      proto.SerializeToString()
  )
