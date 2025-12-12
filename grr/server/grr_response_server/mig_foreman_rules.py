#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_proto import jobs_pb2
from grr_response_server import foreman_rules


def ToProtoForemanOsClientRule(
    rdf: foreman_rules.ForemanOsClientRule,
) -> jobs_pb2.ForemanOsClientRule:
  return rdf.AsPrimitiveProto()


def ToRDFForemanOsClientRule(
    proto: jobs_pb2.ForemanOsClientRule,
) -> foreman_rules.ForemanOsClientRule:
  return foreman_rules.ForemanOsClientRule.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoForemanLabelClientRule(
    rdf: foreman_rules.ForemanLabelClientRule,
) -> jobs_pb2.ForemanLabelClientRule:
  return rdf.AsPrimitiveProto()


def ToRDFForemanLabelClientRule(
    proto: jobs_pb2.ForemanLabelClientRule,
) -> foreman_rules.ForemanLabelClientRule:
  return foreman_rules.ForemanLabelClientRule.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoForemanRegexClientRule(
    rdf: foreman_rules.ForemanRegexClientRule,
) -> jobs_pb2.ForemanRegexClientRule:
  return rdf.AsPrimitiveProto()


def ToRDFForemanRegexClientRule(
    proto: jobs_pb2.ForemanRegexClientRule,
) -> foreman_rules.ForemanRegexClientRule:
  return foreman_rules.ForemanRegexClientRule.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoForemanIntegerClientRule(
    rdf: foreman_rules.ForemanIntegerClientRule,
) -> jobs_pb2.ForemanIntegerClientRule:
  return rdf.AsPrimitiveProto()


def ToRDFForemanIntegerClientRule(
    proto: jobs_pb2.ForemanIntegerClientRule,
) -> foreman_rules.ForemanIntegerClientRule:
  return foreman_rules.ForemanIntegerClientRule.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoForemanRuleAction(
    rdf: foreman_rules.ForemanRuleAction,
) -> jobs_pb2.ForemanRuleAction:
  return rdf.AsPrimitiveProto()


def ToRDFForemanRuleAction(
    proto: jobs_pb2.ForemanRuleAction,
) -> foreman_rules.ForemanRuleAction:
  return foreman_rules.ForemanRuleAction.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoForemanClientRule(
    rdf: foreman_rules.ForemanClientRule,
) -> jobs_pb2.ForemanClientRule:
  return rdf.AsPrimitiveProto()


def ToRDFForemanClientRule(
    proto: jobs_pb2.ForemanClientRule,
) -> foreman_rules.ForemanClientRule:
  return foreman_rules.ForemanClientRule.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoForemanClientRuleSet(
    rdf: foreman_rules.ForemanClientRuleSet,
) -> jobs_pb2.ForemanClientRuleSet:
  return rdf.AsPrimitiveProto()


def ToRDFForemanClientRuleSet(
    proto: jobs_pb2.ForemanClientRuleSet,
) -> foreman_rules.ForemanClientRuleSet:
  return foreman_rules.ForemanClientRuleSet.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoForemanRule(rdf: foreman_rules.ForemanRule) -> jobs_pb2.ForemanRule:
  return rdf.AsPrimitiveProto()


def ToRDFForemanRule(proto: jobs_pb2.ForemanRule) -> foreman_rules.ForemanRule:
  return foreman_rules.ForemanRule.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoForemanCondition(
    rdf: foreman_rules.ForemanCondition,
) -> jobs_pb2.ForemanCondition:
  return rdf.AsPrimitiveProto()


def ToRDFForemanCondition(
    proto: jobs_pb2.ForemanCondition,
) -> foreman_rules.ForemanCondition:
  return foreman_rules.ForemanCondition.FromSerializedBytes(
      proto.SerializeToString()
  )
