#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""
from grr_response_server.rdfvalues import rrg as rdf_rrg
from grr_response_proto.rrg import fs_pb2
from grr_response_proto.rrg import startup_pb2


def ToProtoPath(rdf: rdf_rrg.Path) -> fs_pb2.Path:
  return rdf.AsPrimitiveProto()


def ToRDFPath(proto: fs_pb2.Path) -> rdf_rrg.Path:
  return rdf_rrg.Path.FromSerializedBytes(proto.SerializeToString())


def ToProtoVersion(rdf: rdf_rrg.Version) -> startup_pb2.Version:
  return rdf.AsPrimitiveProto()


def ToRDFVersion(proto: startup_pb2.Version) -> rdf_rrg.Version:
  return rdf_rrg.Version.FromSerializedBytes(proto.SerializeToString())


def ToProtoMetadata(rdf: rdf_rrg.Metadata) -> startup_pb2.Metadata:
  return rdf.AsPrimitiveProto()


def ToRDFMetadata(proto: startup_pb2.Metadata) -> rdf_rrg.Metadata:
  return rdf_rrg.Metadata.FromSerializedBytes(proto.SerializeToString())


def ToProtoStartup(rdf: rdf_rrg.Startup) -> startup_pb2.Startup:
  return rdf.AsPrimitiveProto()


def ToRDFStartup(proto: startup_pb2.Startup) -> rdf_rrg.Startup:
  return rdf_rrg.Startup.FromSerializedBytes(proto.SerializeToString())
