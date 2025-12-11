#!/usr/bin/env python
"""Foreman rules RDFValue classes."""

import itertools

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.lib.rdfvalues import standard as rdf_standard
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import jobs_pb2


class ForemanClientRuleBase(rdf_structs.RDFProtoStruct):
  """Abstract base class of foreman client rules."""

  def Evaluate(self, client_info):
    """Evaluates the rule represented by this object.

    Args:
      client_info: A `db.ClientFullInfo` instance.

    Returns:
      A bool value of the evaluation.
    """
    raise NotImplementedError

  def Validate(self):
    raise NotImplementedError


class ForemanOsClientRule(ForemanClientRuleBase):
  """This rule will fire if the client OS is marked as true in the proto."""

  protobuf = jobs_pb2.ForemanOsClientRule

  def Evaluate(self, client_info):
    value = client_info.last_snapshot.knowledge_base.os

    if not value:
      return False

    return (
        (self.os_windows and value.startswith("Windows"))
        or (self.os_linux and value.startswith("Linux"))
        or (self.os_darwin and value.startswith("Darwin"))
    )

  def Validate(self):
    pass


class ForemanLabelClientRule(ForemanClientRuleBase):
  """This rule will fire if the client has the selected label."""

  protobuf = jobs_pb2.ForemanLabelClientRule

  def Evaluate(self, client_info):
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

    client_label_names = [label.name for label in client_info.labels]

    return quantifier((name in client_label_names) for name in self.label_names)

  def Validate(self):
    pass


class ForemanRegexClientRule(ForemanClientRuleBase):
  """The Foreman schedules flows based on these rules firing."""

  protobuf = jobs_pb2.ForemanRegexClientRule
  rdf_deps = [
      rdf_standard.RegularExpression,
  ]

  def _ResolveField(self, field, client_info):

    fsf = ForemanRegexClientRule.ForemanStringField
    snapshot = client_info.last_snapshot
    startup_info = client_info.last_startup_info

    if field == fsf.UNSET:
      raise ValueError(
          "Received regex rule without a valid field specification."
      )
    elif field == fsf.USERNAMES:
      return " ".join(user.username for user in snapshot.knowledge_base.users)
    elif field == fsf.FQDN:
      return snapshot.knowledge_base.fqdn
    elif field == fsf.HOST_IPS:
      return " ".join(snapshot.GetIPAddresses())
    elif field == fsf.CLIENT_NAME:
      if startup_info:
        return startup_info.client_info.client_name
      else:
        return ""
    elif field == fsf.CLIENT_DESCRIPTION:
      if startup_info:
        return startup_info.client_info.client_description
      else:
        return ""
    elif field == fsf.SYSTEM:
      return snapshot.knowledge_base.os
    elif field == fsf.MAC_ADDRESSES:
      return " ".join(snapshot.GetMacAddresses())
    elif field == fsf.KERNEL_VERSION:
      return snapshot.kernel
    elif field == fsf.OS_VERSION:
      return snapshot.os_version
    elif field == fsf.OS_RELEASE:
      return snapshot.os_release
    elif field == fsf.CLIENT_LABELS:
      system_labels = snapshot.startup_info.client_info.labels
      user_labels = [l.name for l in client_info.labels]
      return " ".join(itertools.chain(system_labels, user_labels))
    elif field == fsf.CLIENT_ID:
      return snapshot.client_id
    else:
      raise ValueError("Unexpected foreman field: %s." % field)

  def Evaluate(self, client_info):
    value = self._ResolveField(self.field, client_info)

    return self.attribute_regex.Search(value)

  def Validate(self):
    if self.field == ForemanRegexClientRule.ForemanStringField.UNSET:
      raise ValueError("ForemanRegexClientRule rule invalid - field not set.")


class ForemanIntegerClientRule(ForemanClientRuleBase):
  """This rule will fire if the expression operator(attribute, value) is true."""

  protobuf = jobs_pb2.ForemanIntegerClientRule
  rdf_deps = []

  def _ResolveField(self, field, client_info):
    if field == ForemanIntegerClientRule.ForemanIntegerField.UNSET:
      raise ValueError(
          "Received integer rule without a valid field specification."
      )

    def SecondsOrNone(v):
      if v is None:
        return v
      return v.AsSecondsSinceEpoch()

    startup_info = client_info.last_startup_info
    client_info = client_info.last_snapshot
    if field == ForemanIntegerClientRule.ForemanIntegerField.CLIENT_VERSION:
      return startup_info.client_info.client_version
    elif field == ForemanIntegerClientRule.ForemanIntegerField.INSTALL_TIME:
      return SecondsOrNone(client_info.install_time)
    elif field == ForemanIntegerClientRule.ForemanIntegerField.LAST_BOOT_TIME:
      return SecondsOrNone(client_info.startup_info.boot_time)
    else:
      raise ValueError("Unexpected foreman integer field: %s." % field)

  def Evaluate(self, client_info):
    value = self._ResolveField(self.field, client_info)

    if value is None:
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
      raise ValueError("Unknown operator: %d" % op)

  def Validate(self):
    if self.field == ForemanIntegerClientRule.ForemanIntegerField.UNSET:
      raise ValueError("ForemanIntegerClientRule rule invalid - field not set.")


class ForemanRuleAction(rdf_structs.RDFProtoStruct):
  protobuf = jobs_pb2.ForemanRuleAction
  rdf_deps = [
      rdf_protodict.Dict,
      rdfvalue.SessionID,
  ]


class ForemanClientRule(ForemanClientRuleBase):
  """Base class proto for foreman client rule protos."""

  protobuf = jobs_pb2.ForemanClientRule
  rdf_deps = [
      ForemanIntegerClientRule,
      ForemanLabelClientRule,
      ForemanOsClientRule,
      ForemanRegexClientRule,
  ]

  def Evaluate(self, client_info):
    return self.UnionCast().Evaluate(client_info)

  def Validate(self):
    self.UnionCast().Validate()


class ForemanClientRuleSet(rdf_structs.RDFProtoStruct):
  """This proto holds rules and the strategy used to evaluate them."""

  protobuf = jobs_pb2.ForemanClientRuleSet
  rdf_deps = [
      ForemanClientRule,
  ]

  def Evaluate(self, client_info):
    """Evaluates rules held in the rule set.

    Args:
      client_info: A client_info dict as returned by ReadFullInfoClient.

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

    return quantifier(rule.Evaluate(client_info) for rule in self.rules)

  def Validate(self):
    for rule in self.rules:
      rule.Validate()


class ForemanRule(rdf_structs.RDFProtoStruct):
  """A Foreman rule RDF value."""

  protobuf = jobs_pb2.ForemanRule
  rdf_deps = [
      ForemanClientRuleSet,
      ForemanRuleAction,
      rdfvalue.RDFDatetime,
  ]

  def Validate(self):
    self.client_rule_set.Validate()

  @property
  def hunt_id(self):
    """Returns hunt id of this rule's actions or None if there's none."""
    for action in self.actions or []:
      if action.hunt_id is not None:
        return action.hunt_id

  def GetLifetime(self):
    if self.expires < self.created:
      raise ValueError("Rule expires before it was created.")
    return self.expires - self.created


class ForemanCondition(rdf_structs.RDFProtoStruct):
  """A ForemanCondition RDF value."""

  protobuf = jobs_pb2.ForemanCondition
  rdf_deps = [
      ForemanClientRuleSet,
      rdfvalue.RDFDatetime,
  ]

  def Validate(self):
    self.client_rule_set.Validate()

  def Evaluate(self, client_data):
    return self.client_rule_set.Evaluate(client_data)

  def GetLifetime(self):
    if self.expiration_time < self.creation_time:
      raise ValueError("Rule expires before it was created.")
    return self.expiration_time - self.creation_time
