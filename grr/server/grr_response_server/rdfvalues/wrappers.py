#!/usr/bin/env python
"""RDFValues for common proto wrappers."""

from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto.api import config_pb2

# Trying to reconcile proto and rdfvalue types is not worth the effort of
# using the common proto wrappers.
#
# These are curretnly useful in places that use RDFPrimitives directly (mixed
# with RDFProtoStructs), such as:
#  * Config options - involves reconciling the stubby/http, opensource/internal
#    differences, and how we build and rely on type metadata.
#  * Client action responses - involves updating all client actions to return
#    a proto instead of primitive types directly.


class StringValue(rdf_structs.RDFProtoStruct):
  protobuf = config_pb2.StringValue


class Int64Value(rdf_structs.RDFProtoStruct):
  protobuf = config_pb2.Int64Value


class BoolValue(rdf_structs.RDFProtoStruct):
  protobuf = config_pb2.BoolValue


class BytesValue(rdf_structs.RDFProtoStruct):
  protobuf = config_pb2.BytesValue
