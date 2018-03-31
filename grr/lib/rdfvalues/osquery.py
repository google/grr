'''
AFF4 RDFValue implementations for OSQuery client information.


Created on Mar 23, 2018

@author: ashaman
'''

from grr.lib.rdfvalues import structs
from grr_response_proto import osquery_pb2


class OSQueryRunQueryResult(structs.RDFProtoStruct):
  """Result of OSQuery SQL."""
  protobuf = osquery_pb2.OSQueryRunQueryResult


class OSQueryRunQueryArgs(structs.RDFProtoStruct):
  """Execute OSQuery SQL."""
  protobuf = osquery_pb2.OSQueryRunQueryArgs