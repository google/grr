#!/usr/bin/env python
"""RDFValue implementations for hunts."""



from grr.lib import output_plugin
from grr.lib import rdfvalue
from grr.lib.rdfvalues import client
from grr.lib.rdfvalues import stats
from grr.lib.rdfvalues import structs as rdf_structs
from grr.proto import flows_pb2
from grr.proto import jobs_pb2
from grr.server import foreman


class HuntNotification(rdf_structs.RDFProtoStruct):
  protobuf = jobs_pb2.HuntNotification
  rdf_deps = [
      client.ClientURN,
      rdfvalue.SessionID,
  ]


class HuntContext(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.HuntContext
  rdf_deps = [
      client.ClientResources,
      stats.ClientResourcesStats,
      rdfvalue.RDFDatetime,
      rdfvalue.SessionID,
  ]


class HuntRunnerArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.HuntRunnerArgs
  rdf_deps = [
      rdfvalue.Duration,
      foreman.ForemanClientRuleSet,
      output_plugin.OutputPluginDescriptor,
      rdfvalue.RDFURN,
  ]

  def Validate(self):
    if self.HasField("client_rule_set"):
      self.client_rule_set.Validate()


class HuntError(rdf_structs.RDFProtoStruct):
  """An RDFValue class representing a hunt error."""
  protobuf = jobs_pb2.HuntError
  rdf_deps = [
      client.ClientURN,
  ]
