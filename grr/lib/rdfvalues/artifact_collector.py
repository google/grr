#!/usr/bin/env python
"""rdf value representation for artifact collector parameters."""
from grr.lib import rdfvalue
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import artifact_pb2
from grr.server.grr_response_server import artifact_registry


class ExtendedSource(rdf_structs.RDFProtoStruct):
  """An RDFValue representing a source and everything it depends on."""
  protobuf = artifact_pb2.ExtendedSource
  rdf_deps = [
      artifact_registry.ArtifactSource,
      rdfvalue.ByteSize,
  ]


class ExtendedArtifact(rdf_structs.RDFProtoStruct):
  """An RDFValue representing an artifact with its extended sources."""
  protobuf = artifact_pb2.ExtendedArtifact
  rdf_deps = [
      ExtendedSource,
      artifact_registry.ArtifactName,
  ]


class ArtifactCollectorArgs(rdf_structs.RDFProtoStruct):
  """An RDFValue representation of an artifact bundle."""
  protobuf = artifact_pb2.ArtifactCollectorArgs
  rdf_deps = [ExtendedArtifact, rdf_client.KnowledgeBase]


class ArtifactCollectorResult(rdf_structs.RDFProtoStruct):
  """An RDFValue representation of the result of the collection results."""
  protobuf = artifact_pb2.ArtifactCollectorResult
