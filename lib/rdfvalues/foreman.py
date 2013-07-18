#!/usr/bin/env python
# Copyright 2011 Google Inc. All Rights Reserved.
"""RDFValue instances related to the foreman implementation."""


from grr.lib import rdfvalue
from grr.lib import type_info
from grr.proto import jobs_pb2


class ForemanRuleAction(rdfvalue.RDFProtoStruct):
  protobuf = jobs_pb2.ForemanRuleAction


class ForemanAttributeRegex(rdfvalue.RDFProtoStruct):
  protobuf = jobs_pb2.ForemanAttributeRegex


class ForemanAttributeInteger(rdfvalue.RDFProtoStruct):
  protobuf = jobs_pb2.ForemanAttributeInteger


class ForemanRule(rdfvalue.RDFProtoStruct):
  """A Foreman rule RDF value."""
  protobuf = jobs_pb2.ForemanRule

  rdf_map = dict(regex_rules=ForemanAttributeRegex,
                 integer_rules=ForemanAttributeInteger,
                 actions=ForemanRuleAction,
                 created=rdfvalue.RDFDatetime,
                 expires=rdfvalue.RDFDatetime,
                 description=rdfvalue.RDFString)

  @property
  def hunt_id(self):
    """Returns hunt id of this rule's actions or None if there's none."""
    for action in self.actions or []:
      if action.hunt_id is not None:
        return action.hunt_id


class ForemanRules(rdfvalue.RDFValueArray):
  """A list of rules that the foreman will apply."""
  rdf_type = ForemanRule


class ForemanAttributeRegexType(type_info.RDFValueType):
  """A Type for handling the ForemanAttributeRegex."""

  child_descriptor = type_info.TypeDescriptorSet(
      type_info.String(
          name="path",
          description=("A relative path under the client for which "
                       "the attribute applies"),
          default="/"),

      type_info.String(
          name="attribute_name",
          description="The attribute to match",
          default="System"),

      type_info.RegularExpression(
          name="attribute_regex",
          description="Regular expression to apply to an attribute",
          default=".*"),
      )

  def __init__(self, **kwargs):
    defaults = dict(name="foreman_attributes",
                    rdfclass=rdfvalue.ForemanAttributeRegex)

    defaults.update(kwargs)
    super(ForemanAttributeRegexType, self).__init__(**defaults)


class ForemanAttributeIntegerType(type_info.RDFValueType):
  """A type for handling the ForemanAttributeInteger."""

  child_descriptor = type_info.TypeDescriptorSet(
      type_info.String(
          name="path",
          description=("A relative path under the client for which "
                       "the attribute applies"),
          default="/"),

      type_info.String(
          name="attribute_name",
          description="The attribute to match.",
          default="Version"),

      type_info.SemanticEnum(
          name="operator",
          description="Comparison operator to apply to integer value",
          enum_container=rdfvalue.ForemanAttributeInteger.Operator,
          default=rdfvalue.ForemanAttributeInteger.Operator.EQUAL),

      type_info.Integer(
          name="value",
          description="Value to compare to",
          default=0),
      )

  def __init__(self, **kwargs):
    defaults = dict(name="foreman_attributes",
                    rdfclass=rdfvalue.ForemanAttributeInteger)

    defaults.update(kwargs)
    super(ForemanAttributeIntegerType, self).__init__(**defaults)
