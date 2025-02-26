#!/usr/bin/env python
"""A module with RDF wrappers for RRG Protocol Buffers messages."""

from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.lib.rdfvalues import wkt as rdf_wkt
from grr_response_proto.rrg import fs_pb2 as rrg_fs_pb2
from grr_response_proto.rrg import startup_pb2 as rrg_startup_pb2


class Path(rdf_structs.RDFProtoStruct):
  """An RDF wrapper for the `Path` message."""

  protobuf = rrg_fs_pb2.Path


class Version(rdf_structs.RDFProtoStruct):
  """An RDF wrapper for the `Version` message."""

  protobuf = rrg_startup_pb2.Version


class Metadata(rdf_structs.RDFProtoStruct):
  """An RDF wrapper for the `Metadata` message."""

  protobuf = rrg_startup_pb2.Metadata
  rdf_deps = [
      Version,
      rdf_wkt.Timestamp,
  ]


class Startup(rdf_structs.RDFProtoStruct):
  """An RDF wrapper for the `Startup` message."""

  protobuf = rrg_startup_pb2.Startup
  rdf_deps = [
      Metadata,
      Path,
      rdf_wkt.Timestamp,
  ]
