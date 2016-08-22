#!/usr/bin/env python
"""RDFValue implementations for hunts."""



from grr.lib.rdfvalues import flows as rdf_flows
from grr.lib.rdfvalues import structs as rdf_structs
from grr.proto import flows_pb2
from grr.proto import jobs_pb2


class HuntNotification(rdf_structs.RDFProtoStruct):
  protobuf = jobs_pb2.HuntNotification


class HuntContext(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.HuntContext

  # TODO(user): A hunt runner should never even check...
  @property
  def state(self):
    return rdf_flows.FlowContext.State.RUNNING


class HuntRunnerArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.HuntRunnerArgs

  def Validate(self):
    if self.HasField("client_rule_set"):
      self.client_rule_set.Validate()


class HuntError(rdf_structs.RDFProtoStruct):
  """An RDFValue class representing a hunt error."""
  protobuf = jobs_pb2.HuntError
