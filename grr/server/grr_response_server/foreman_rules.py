#!/usr/bin/env python
"""Foreman rules RDFValue classes."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import itertools

from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.lib.rdfvalues import standard as rdf_standard
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import jobs_pb2


# Cannot use data_store here, because of circular dependency.
def RelationalDBReadEnabled():
  return config.CONFIG["Database.useForReads"]


# TODO(amoser): Rename client_obj once relational db becomes standard.
class ForemanClientRuleBase(rdf_structs.RDFProtoStruct):
  """Abstract base class of foreman client rules."""

  def Evaluate(self, client_obj):
    """Evaluates the rule represented by this object.

    Args:
      client_obj: Either an aff4 client object or a `db.ClientFullInfo` instance
                  if the relational db is used for reading.

    Returns:
      A bool value of the evaluation.
    """
    raise NotImplementedError

  def Validate(self):
    raise NotImplementedError


class ForemanOsClientRule(ForemanClientRuleBase):
  """This rule will fire if the client OS is marked as true in the proto."""
  protobuf = jobs_pb2.ForemanOsClientRule

  def Evaluate(self, client_obj):
    if RelationalDBReadEnabled():
      value = client_obj.last_snapshot.knowledge_base.os
    else:
      value = client_obj.Get(client_obj.Schema.SYSTEM)

    if not value:
      return False

    value = utils.SmartStr(value)

    return ((self.os_windows and value.startswith("Windows")) or
            (self.os_linux and value.startswith("Linux")) or
            (self.os_darwin and value.startswith("Darwin")))

  def Validate(self):
    pass


class ForemanLabelClientRule(ForemanClientRuleBase):
  """This rule will fire if the client has the selected label."""
  protobuf = jobs_pb2.ForemanLabelClientRule

  def Evaluate(self, client_obj):
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

    if RelationalDBReadEnabled():
      client_label_names = [label.name for label in client_obj.labels]
    else:
      client_label_names = set(client_obj.GetLabelsNames())

    return quantifier((name in client_label_names) for name in self.label_names)

  def Validate(self):
    pass


class ForemanRegexClientRule(ForemanClientRuleBase):
  """The Foreman schedules flows based on these rules firing."""
  protobuf = jobs_pb2.ForemanRegexClientRule
  rdf_deps = [
      rdf_standard.RegularExpression,
  ]

  def _ResolveFieldAFF4(self, field, client_obj):

    fsf = ForemanRegexClientRule.ForemanStringField

    if field == fsf.UNSET:
      raise ValueError(
          "Received regex rule without a valid field specification.")
    elif field == fsf.USERNAMES:
      res = client_obj.Get(client_obj.Schema.USERNAMES)
    elif field == fsf.UNAME:
      res = client_obj.Get(client_obj.Schema.UNAME)
    elif field == fsf.FQDN:
      res = client_obj.Get(client_obj.Schema.FQDN)
    elif field == fsf.HOST_IPS:
      res = client_obj.Get(client_obj.Schema.HOST_IPS)
      if res:
        res = utils.SmartStr(res).replace("\n", " ")
    elif field == fsf.CLIENT_NAME:
      res = None
      info = client_obj.Get(client_obj.Schema.CLIENT_INFO)
      if info:
        res = info.client_name
    elif field == fsf.CLIENT_DESCRIPTION:
      res = None
      info = client_obj.Get(client_obj.Schema.CLIENT_INFO)
      if info:
        res = info.client_description
    elif field == fsf.SYSTEM:
      res = client_obj.Get(client_obj.Schema.SYSTEM)
    elif field == fsf.MAC_ADDRESSES:
      res = client_obj.Get(client_obj.Schema.MAC_ADDRESS)
      if res:
        res = utils.SmartStr(res).replace("\n", " ")
    elif field == fsf.KERNEL_VERSION:
      res = client_obj.Get(client_obj.Schema.KERNEL_VERSION)
    elif field == fsf.OS_VERSION:
      res = client_obj.Get(client_obj.Schema.OS_VERSION)
    elif field == fsf.OS_RELEASE:
      res = client_obj.Get(client_obj.Schema.OS_RELEASE)
    elif field == fsf.CLIENT_LABELS:
      res = " ".join(client_obj.GetLabelsNames())

    if res is None:
      return ""
    return utils.SmartStr(res)

  def _ResolveField(self, field, client_info):

    fsf = ForemanRegexClientRule.ForemanStringField
    client_obj = client_info.last_snapshot
    startup_info = client_info.last_startup_info

    if field == fsf.UNSET:
      raise ValueError(
          "Received regex rule without a valid field specification.")
    elif field == fsf.USERNAMES:
      res = " ".join(user.username for user in client_obj.knowledge_base.users)
    elif field == fsf.UNAME:
      res = client_obj.Uname()
    elif field == fsf.FQDN:
      res = client_obj.knowledge_base.fqdn
    elif field == fsf.HOST_IPS:
      res = " ".join(client_obj.GetIPAddresses())
    elif field == fsf.CLIENT_NAME:
      res = startup_info and startup_info.client_info.client_name
    elif field == fsf.CLIENT_DESCRIPTION:
      res = startup_info and startup_info.client_info.client_description
    elif field == fsf.SYSTEM:
      res = client_obj.knowledge_base.os
    elif field == fsf.MAC_ADDRESSES:
      res = " ".join(client_obj.GetMacAddresses())
    elif field == fsf.KERNEL_VERSION:
      res = client_obj.kernel
    elif field == fsf.OS_VERSION:
      res = client_obj.os_version
    elif field == fsf.OS_RELEASE:
      res = client_obj.os_release
    elif field == fsf.CLIENT_LABELS:
      system_labels = client_obj.startup_info.client_info.labels
      user_labels = [l.name for l in client_info.labels]
      res = " ".join(itertools.chain(system_labels, user_labels))

    if res is None:
      return ""
    return utils.SmartStr(res)

  def Evaluate(self, client_obj):
    if RelationalDBReadEnabled():
      value = self._ResolveField(self.field, client_obj)
    else:
      value = self._ResolveFieldAFF4(self.field, client_obj)

    return self.attribute_regex.Search(value)

  def Validate(self):
    if self.field == ForemanRegexClientRule.ForemanStringField.UNSET:
      raise ValueError("ForemanRegexClientRule rule invalid - field not set.")


class ForemanIntegerClientRule(ForemanClientRuleBase):
  """This rule will fire if the expression operator(attribute, value) is true.
  """
  protobuf = jobs_pb2.ForemanIntegerClientRule
  rdf_deps = []

  def _ResolveFieldAFF4(self, field, client_obj):
    if field == ForemanIntegerClientRule.ForemanIntegerField.UNSET:
      raise ValueError(
          "Received integer rule without a valid field specification.")

    if field == ForemanIntegerClientRule.ForemanIntegerField.CLIENT_VERSION:
      info = client_obj.Get(client_obj.Schema.CLIENT_INFO)
      if not info:
        return info
      return int(info.client_version or 0)

    elif field == ForemanIntegerClientRule.ForemanIntegerField.INSTALL_TIME:
      res = client_obj.Get(client_obj.Schema.INSTALL_DATE)
    elif field == ForemanIntegerClientRule.ForemanIntegerField.LAST_BOOT_TIME:
      res = client_obj.Get(client_obj.Schema.LAST_BOOT_TIME)
    elif field == ForemanIntegerClientRule.ForemanIntegerField.CLIENT_CLOCK:
      res = client_obj.Get(client_obj.Schema.CLOCK)

    if res is None:
      return
    return res.AsSecondsSinceEpoch()

  def _ResolveField(self, field, client_info):
    if field == ForemanIntegerClientRule.ForemanIntegerField.UNSET:
      raise ValueError(
          "Received integer rule without a valid field specification.")

    startup_info = client_info.last_startup_info
    md = client_info.metadata
    client_obj = client_info.last_snapshot
    if field == ForemanIntegerClientRule.ForemanIntegerField.CLIENT_VERSION:
      return startup_info.client_info.client_version
    elif field == ForemanIntegerClientRule.ForemanIntegerField.INSTALL_TIME:
      res = client_obj.install_time
    elif field == ForemanIntegerClientRule.ForemanIntegerField.LAST_BOOT_TIME:
      res = client_obj.startup_info.boot_time
    elif field == ForemanIntegerClientRule.ForemanIntegerField.CLIENT_CLOCK:
      res = md.clock

    if res is None:
      return
    return res.AsSecondsSinceEpoch()

  def Evaluate(self, client_obj):
    if RelationalDBReadEnabled():
      value = self._ResolveField(self.field, client_obj)
    else:
      value = self._ResolveFieldAFF4(self.field, client_obj)

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
  """"Base class" proto for foreman client rule protos."""
  protobuf = jobs_pb2.ForemanClientRule
  rdf_deps = [
      ForemanIntegerClientRule,
      ForemanLabelClientRule,
      ForemanOsClientRule,
      ForemanRegexClientRule,
  ]

  def Evaluate(self, client_obj):
    return self.UnionCast().Evaluate(client_obj)

  def Validate(self):
    self.UnionCast().Validate()


class ForemanClientRuleSet(rdf_structs.RDFProtoStruct):
  """This proto holds rules and the strategy used to evaluate them."""
  protobuf = jobs_pb2.ForemanClientRuleSet
  rdf_deps = [
      ForemanClientRule,
  ]

  def Evaluate(self, client_obj):
    """Evaluates rules held in the rule set.

    Args:
      client_obj: Either an aff4 client object or a client_info dict as returned
                  by ReadFullInfoClient if the relational db is used for
                  reading.

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

    return quantifier(rule.Evaluate(client_obj) for rule in self.rules)

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


class ForemanRules(rdf_protodict.RDFValueArray):
  """A list of rules that the foreman will apply."""
  rdf_type = ForemanRule
