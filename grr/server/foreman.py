#!/usr/bin/env python
# Copyright 2011 Google Inc. All Rights Reserved.
"""RDFValue instances related to the foreman implementation."""


import itertools

from grr.lib import aff4
from grr.lib import utils
from grr.lib.rdfvalues import protodict as rdf_protodict
from grr.lib.rdfvalues import structs as rdf_structs
from grr.proto import jobs_pb2


class ForemanClientRuleSet(rdf_structs.RDFProtoStruct):
  """This proto holds rules and the strategy used to evaluate them."""
  protobuf = jobs_pb2.ForemanClientRuleSet

  def GetPathsToCheck(self):
    """Returns aff4 paths to be opened as objects passed to Evaluate."""
    return set(itertools.chain.from_iterable(rule.GetPathsToCheck()
                                             for rule in self.rules))

  def Evaluate(self, objects, client_id):
    """Evaluates rules held in the rule set.

    Args:
      objects: A dict that maps fd.urn to fd for all file descriptors fd
          corresponding to the aff4 paths returned by the GetPathsToCheck
          method of this object.
      client_id: An aff4 client id object.

    Returns:
      A bool value of the evaluation.

    Raises:
      ValueError: The match mode is of unknown value.
    """
    if self.match_mode == ForemanClientRuleSet.MatchMode.MATCH_ALL:
      quantifier = all
    elif self.match_mode == ForemanClientRuleSet.MatchMode.MATCH_ANY:
      quantifier = any
    else:
      raise ValueError("Unexpected match mode value: %s" % self.match_mode)

    return quantifier(rule.Evaluate(objects, client_id) for rule in self.rules)

  def Validate(self):
    for rule in self.rules:
      rule.Validate()


class ForemanClientRuleBase(rdf_structs.RDFProtoStruct):
  """Abstract base class of foreman client rules."""

  def GetPathsToCheck(self):
    """Returns aff4 paths to be opened as objects passed to Evaluate.

    Optional overrides of this method should return an iterable filled with
    strs representing the aff4 paths to be opened.

    Returns:
      An iterable filled with strs representing the aff4 paths to be opened.
    """
    return ["/"]

  def Evaluate(self, objects, client_id):
    """Evaluates the rule represented by this object.

    Args:
      objects: A dict that maps fd.urn to fd for all file descriptors fd
          corresponding to the aff4 paths returned by the GetPathsToCheck
          method of this object.
      client_id: An aff4 client id object.

    Returns:
      A bool value of the evaluation.
    """
    raise NotImplementedError

  def Validate(self):
    raise NotImplementedError


class ForemanClientRule(ForemanClientRuleBase):
  """"Base class" proto for foreman client rule protos."""
  protobuf = jobs_pb2.ForemanClientRule

  def GetPathsToCheck(self):
    return self.UnionCast().GetPathsToCheck()

  def Evaluate(self, objects, client_id):
    return self.UnionCast().Evaluate(objects, client_id)

  def Validate(self):
    self.UnionCast().Validate()


class ForemanOsClientRule(ForemanClientRuleBase):
  """This rule will fire if the client OS is marked as true in the proto."""
  protobuf = jobs_pb2.ForemanOsClientRule

  def Evaluate(self, objects, client_id):
    try:
      fd = objects[client_id]
      attribute = aff4.Attribute.NAMES["System"]
    except KeyError:
      return False

    value = utils.SmartStr(fd.Get(attribute))

    return ((self.os_windows and value.startswith("Windows")) or
            (self.os_linux and value.startswith("Linux")) or
            (self.os_darwin and value.startswith("Darwin")))

  def Validate(self):
    pass


class ForemanLabelClientRule(ForemanClientRuleBase):
  """This rule will fire if the client has the selected label."""
  protobuf = jobs_pb2.ForemanLabelClientRule

  def Evaluate(self, objects, client_id):
    try:
      fd = objects[client_id]
    except KeyError:
      return False

    if self.match_mode == ForemanLabelClientRule.MatchMode.MATCH_ALL:
      quantifier = all
    elif self.match_mode == ForemanLabelClientRule.MatchMode.MATCH_ANY:
      quantifier = any
    elif self.match_mode == ForemanLabelClientRule.MatchMode.DOES_NOT_MATCH_ALL:
      quantifier = lambda iterable: not all(iterable)
    elif self.match_mode == ForemanLabelClientRule.MatchMode.DOES_NOT_MATCH_ANY:
      quantifier = lambda iterable: not any(iterable)
    else:
      raise ValueError("Unexpected match mode value: %s" % self.match_mode)

    client_label_names = set(fd.GetLabelsNames())

    return quantifier((name in client_label_names) for name in self.label_names)

  def Validate(self):
    pass


class ForemanRegexClientRule(ForemanClientRuleBase):
  """The Foreman schedules flows based on these rules firing."""
  protobuf = jobs_pb2.ForemanRegexClientRule

  def GetPathsToCheck(self):
    return [self.path]

  def Evaluate(self, objects, client_id):
    path = client_id.Add(self.path)
    try:
      fd = objects[path]
      attribute = aff4.Attribute.NAMES[self.attribute_name]
    except KeyError:
      return False

    value = utils.SmartStr(fd.Get(attribute))

    return self.attribute_regex.Search(value)

  def Validate(self):
    if not self.attribute_name:
      raise ValueError("ForemanRegexClientRule rule invalid - "
                       "attribute name not set.")

    self.attribute_name.Validate()


class ForemanIntegerClientRule(ForemanClientRuleBase):
  """This rule will fire if the expression operator(attribute, value) is true.
  """
  protobuf = jobs_pb2.ForemanIntegerClientRule

  def GetPathsToCheck(self):
    return [self.path]

  def Evaluate(self, objects, client_id):
    path = client_id.Add(self.path)
    try:
      fd = objects[path]
      attribute = aff4.Attribute.NAMES[self.attribute_name]
    except KeyError:
      return False

    try:
      value = int(fd.Get(attribute))
    except (ValueError, TypeError):
      # Not an integer attribute.
      return False

    op = self.operator
    if op == ForemanIntegerClientRule.Operator.LESS_THAN:
      return value < self.value
    elif op == ForemanIntegerClientRule.Operator.GREATER_THAN:
      return value > self.value
    elif op == ForemanIntegerClientRule.Operator.EQUAL:
      return value == self.value
    else:
      # Unknown operator.
      return False

  def Validate(self):
    if not self.attribute_name:
      raise ValueError("ForemanIntegerClientRule rule invalid - "
                       "attribute name not set.")

    self.attribute_name.Validate()


class ForemanRuleAction(rdf_structs.RDFProtoStruct):
  protobuf = jobs_pb2.ForemanRuleAction


class ForemanRule(rdf_structs.RDFProtoStruct):
  """A Foreman rule RDF value."""
  protobuf = jobs_pb2.ForemanRule

  def Validate(self):
    self.client_rule_set.Validate()

  @property
  def hunt_id(self):
    """Returns hunt id of this rule's actions or None if there's none."""
    for action in self.actions or []:
      if action.hunt_id is not None:
        return action.hunt_id


class ForemanRules(rdf_protodict.RDFValueArray):
  """A list of rules that the foreman will apply."""
  rdf_type = ForemanRule
