#!/usr/bin/env python
"""Implementations of RDFValues used in GRR config options definitions."""


from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import config_pb2


class AdminUIClientWarningRule(rdf_structs.RDFProtoStruct):
  protobuf = config_pb2.AdminUIClientWarningRule


class AdminUIClientWarningsConfigOption(rdf_structs.RDFProtoStruct):
  protobuf = config_pb2.AdminUIClientWarningsConfigOption
  rdf_deps = [AdminUIClientWarningRule]
