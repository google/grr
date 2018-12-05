#!/usr/bin/env python
"""WMI RDF values."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import sysinfo_pb2


class WMIActiveScriptEventConsumer(rdf_structs.RDFProtoStruct):
  protobuf = sysinfo_pb2.WMIActiveScriptEventConsumer


class WMICommandLineEventConsumer(rdf_structs.RDFProtoStruct):
  protobuf = sysinfo_pb2.WMICommandLineEventConsumer
