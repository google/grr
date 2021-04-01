#!/usr/bin/env python
"""A module with RDF wrappers for large file collection proto messages."""
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import large_file_pb2


class CollectLargeFileArgs(rdf_structs.RDFProtoStruct):
  """An RDF wrapper for arguments of the large file collection action."""

  protobuf = large_file_pb2.CollectLargeFileArgs
  rdf_deps = [
      rdf_paths.PathSpec,
  ]


class CollectLargeFileResult(rdf_structs.RDFProtoStruct):
  """An RDF wrapper for result of the large file collection action."""

  protobuf = large_file_pb2.CollectLargeFileResult
  rdf_deps = []
