#!/usr/bin/env python
"""WMI RDF values."""

from grr.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import sysinfo_pb2


class WMIActiveScriptEventConsumer(rdf_structs.RDFProtoStruct):
  protobuf = sysinfo_pb2.WMIActiveScriptEventConsumer


class WMICommandLineEventConsumer(rdf_structs.RDFProtoStruct):
  protobuf = sysinfo_pb2.WMICommandLineEventConsumer
