#!/usr/bin/env python
"""Implementations of RDFValues used in GRR config options definitions."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import config_pb2


class AdminUIClientWarningRule(rdf_structs.RDFProtoStruct):
  protobuf = config_pb2.AdminUIClientWarningRule


class AdminUIClientWarningsConfigOption(rdf_structs.RDFProtoStruct):
  protobuf = config_pb2.AdminUIClientWarningsConfigOption
  rdf_deps = [AdminUIClientWarningRule]
