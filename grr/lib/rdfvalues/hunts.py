#!/usr/bin/env python
"""RDFValue implementations for hunts."""



from grr import config
from grr.lib import rdfvalue
from grr.lib.rdfvalues import client
from grr.lib.rdfvalues import stats
from grr.lib.rdfvalues import structs as rdf_structs
from grr.proto import flows_pb2
from grr.proto import jobs_pb2
from grr.server import foreman
from grr.server import output_plugin


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
  """Hunt runner arguments definition."""

  protobuf = flows_pb2.HuntRunnerArgs
  rdf_deps = [
      rdfvalue.Duration,
      foreman.ForemanClientRuleSet,
      output_plugin.OutputPluginDescriptor,
      rdfvalue.RDFURN,
  ]

  def __init__(self, initializer=None, **kwargs):
    super(HuntRunnerArgs, self).__init__(initializer=initializer, **kwargs)

    if initializer is None and not self.HasField("crash_limit"):
      self.crash_limit = config.CONFIG["Hunt.default_crash_limit"]

  def Validate(self):
    if self.HasField("client_rule_set"):
      self.client_rule_set.Validate()


class HuntError(rdf_structs.RDFProtoStruct):
  """An RDFValue class representing a hunt error."""
  protobuf = jobs_pb2.HuntError
  rdf_deps = [
      client.ClientURN,
  ]
