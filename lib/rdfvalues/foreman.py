#!/usr/bin/env python
# Copyright 2011 Google Inc. All Rights Reserved.
"""RDFValue instances related to the foreman implementation."""

from grr.lib import rdfvalue
from grr.proto import jobs_pb2


class ForemanRuleAction(rdfvalue.RDFProtoStruct):
  protobuf = jobs_pb2.ForemanRuleAction


class ForemanAttributeRegex(rdfvalue.RDFProtoStruct):
  protobuf = jobs_pb2.ForemanAttributeRegex

  def Validate(self):
    if not self.attribute_name:
      raise ValueError("ForemanAttributeRegex rule invalid - "
                       "not attribute set.")

    self.attribute_name.Validate()


class ForemanAttributeInteger(ForemanAttributeRegex):
  protobuf = jobs_pb2.ForemanAttributeInteger


class ForemanRule(rdfvalue.RDFProtoStruct):
  """A Foreman rule RDF value."""
  protobuf = jobs_pb2.ForemanRule

  def Validate(self):
    for rule in self.regex_rules:
      rule.Validate()

    for rule in self.integer_rules:
      rule.Validate()

  @property
  def hunt_id(self):
    """Returns hunt id of this rule's actions or None if there's none."""
    for action in self.actions or []:
      if action.hunt_id is not None:
        return action.hunt_id


class ForemanRules(rdfvalue.RDFValueArray):
  """A list of rules that the foreman will apply."""
  rdf_type = ForemanRule
