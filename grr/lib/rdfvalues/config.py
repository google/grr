#!/usr/bin/env python
"""Implementations of RDFValues used in GRR config options definitions."""

from grr.lib.rdfvalues import structs
from grr_response_proto import config_pb2


class AdminUIClientWarningRule(structs.RDFProtoStruct):
  protobuf = config_pb2.AdminUIClientWarningRule


class AdminUIClientWarningsConfigOption(structs.RDFProtoStruct):
  protobuf = config_pb2.AdminUIClientWarningsConfigOption
  rdf_deps = [AdminUIClientWarningRule]
