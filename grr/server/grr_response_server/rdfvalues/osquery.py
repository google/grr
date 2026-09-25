#!/usr/bin/env python
"""A module with RDF values wrapping server osquery protobufs."""

from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import osquery_pb2


class OsqueryCollectedFile(rdf_structs.RDFProtoStruct):
  """An RDF wrapper class for the `OsqueryCollectedFile` proto."""

  protobuf = osquery_pb2.OsqueryCollectedFile
  rdf_deps = [rdf_client_fs.StatEntry]
