#!/usr/bin/env python
"""Foreman rules RDFValue classes."""

import itertools
from typing import Optional

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.lib.rdfvalues import standard as rdf_standard
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import jobs_pb2
from grr_response_proto import objects_pb2
from grr_response_server.models import clients as models_clients


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


def EvaluateForemanOsClientRule(
    rule: jobs_pb2.ForemanOsClientRule, client_info: objects_pb2.ClientFullInfo
) -> bool:
  """Evaluates a ForemanOsClientRule against client information.

  Args:
    rule: The `ForemanOsClientRule` proto to evaluate.
    client_info: A `ClientFullInfo` instance containing client data.

  Returns:
    True if the client's OS matches the rule's criteria, False otherwise.
  """
  value: str = client_info.last_snapshot.knowledge_base.os

  if not value:
    return False

  return (
      (rule.os_windows and value.startswith("Windows"))
      or (rule.os_linux and value.startswith("Linux"))
      or (rule.os_darwin and value.startswith("Darwin"))
  )


class ForemanLabelClientRule(ForemanClientRuleBase):
  """This rule will fire if the client has the selected label."""

  protobuf = jobs_pb2.ForemanLabelClientRule


def EvaluateForemanLabelClientRule(
    rule: jobs_pb2.ForemanLabelClientRule,
    client_info: objects_pb2.ClientFullInfo,
) -> bool:
  """Evaluates a ForemanLabelClientRule against client information.

  Args:
    rule: The `ForemanLabelClientRule` proto to evaluate.
    client_info: A `ClientFullInfo` instance containing client data.

  Returns:
    True if the client's labels match the rule's criteria, False otherwise.
  """
  match_mode = jobs_pb2.ForemanLabelClientRule.MatchMode
  if rule.match_mode == match_mode.MATCH_ALL:
    quantifier = all
  elif rule.match_mode == match_mode.MATCH_ANY:
    quantifier = any
  elif rule.match_mode == match_mode.DOES_NOT_MATCH_ALL:
    quantifier = lambda iterable: not all(iterable)
  elif rule.match_mode == match_mode.DOES_NOT_MATCH_ANY:
    quantifier = lambda iterable: not any(iterable)
  else:
    raise ValueError("Unexpected match mode value: %s" % rule.match_mode)

  client_label_names = [label.name for label in client_info.labels]

  return quantifier((name in client_label_names) for name in rule.label_names)


class ForemanRegexClientRule(ForemanClientRuleBase):
  """The Foreman schedules flows based on these rules firing."""

  protobuf = jobs_pb2.ForemanRegexClientRule
  rdf_deps = [
      rdf_standard.RegularExpression,
  ]


def _ResolveStringField(
    field: "jobs_pb2.ForemanRegexClientRule.ForemanStringField",
    client_info: objects_pb2.ClientFullInfo,
) -> str:
  """Resolves the string value of a specified field from client information.

  Args:
    field: The enum value specifying which field to resolve.
    client_info: A `ClientFullInfo` instance containing client data.

  Returns:
    The string representation of the requested field.

  Raises:
    ValueError: If the field specification is UNSET or unknown.
  """
  fsf = jobs_pb2.ForemanRegexClientRule.ForemanStringField
  snapshot = client_info.last_snapshot
  startup_info = client_info.last_startup_info

  if field == fsf.UNSET:
    raise ValueError("Received regex rule without a valid field specification.")
  elif field == fsf.USERNAMES:
    return " ".join(user.username for user in snapshot.knowledge_base.users)
  elif field == fsf.FQDN:
    return snapshot.knowledge_base.fqdn
  elif field == fsf.HOST_IPS:
    return " ".join(models_clients.GetIpAddressesFromClientSnapshot(snapshot))
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
    return " ".join(models_clients.GetMacAddressesFromClientSnapshot(snapshot))
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


def EvaluateForemanRegexClientRule(
    rule: jobs_pb2.ForemanRegexClientRule,
    client_info: objects_pb2.ClientFullInfo,
) -> bool:
  """Evaluates a ForemanRegexClientRule against client information.

  Args:
    rule: The `ForemanRegexClientRule` proto to evaluate.
    client_info: A `ClientFullInfo` instance containing client data.

  Returns:
    True if the specified client field matches the rule's regex, False
    otherwise.
  """
  value = _ResolveStringField(rule.field, client_info)

  reg = rdf_standard.RegularExpression(rule.attribute_regex)
  return bool(reg.Search(value))


class ForemanIntegerClientRule(ForemanClientRuleBase):
  """This rule will fire if the expression operator(attribute, value) is true."""

  protobuf = jobs_pb2.ForemanIntegerClientRule
  rdf_deps = []


def _ResolveIntegerField(
    field: "jobs_pb2.ForemanIntegerClientRule.ForemanIntegerField",
    client_info: objects_pb2.ClientFullInfo,
) -> Optional[int]:
  """Resolves the integer value of a specified field from client information.

  Args:
    field: The enum value specifying which integer field to resolve.
    client_info: A `ClientFullInfo` instance containing client data.

  Returns:
    The integer representation of the requested field, or None if the value
    is not available.

  Raises:
    ValueError: If the field specification is UNSET or unknown.
  """
  fif = jobs_pb2.ForemanIntegerClientRule.ForemanIntegerField
  if field == fif.UNSET:
    raise ValueError(
        "Received integer rule without a valid field specification."
    )

  def MicrosecondsToSeconds(v: int) -> int:
    return v // 1_000_000

  startup_info = client_info.last_startup_info
  client_info = client_info.last_snapshot
  if field == fif.CLIENT_VERSION:
    return startup_info.client_info.client_version
  elif field == fif.INSTALL_TIME:
    if not client_info.HasField("install_time"):
      return None
    return MicrosecondsToSeconds(client_info.install_time)
  elif field == fif.LAST_BOOT_TIME:
    if not client_info.startup_info.HasField("boot_time"):
      return None
    return MicrosecondsToSeconds(client_info.startup_info.boot_time)
  else:
    raise ValueError("Unexpected foreman integer field: %s." % field)


def EvaluateForemanIntegerClientRule(
    rule: jobs_pb2.ForemanIntegerClientRule,
    client_info: objects_pb2.ClientFullInfo,
) -> bool:
  """Evaluates a ForemanIntegerClientRule against client information.

  Args:
    rule: The `ForemanIntegerClientRule` proto to evaluate.
    client_info: A `ClientFullInfo` instance containing client data.

  Returns:
    True if the specified client integer field matches the rule's criteria,
    False otherwise.

  Raises:
    ValueError: If an unknown operator is specified in the rule.
  """
  value = _ResolveIntegerField(rule.field, client_info)

  if value is None:
    return False

  op = rule.operator
  op_enum = jobs_pb2.ForemanIntegerClientRule.Operator
  if op == op_enum.LESS_THAN:
    return value < rule.value
  elif op == op_enum.GREATER_THAN:
    return value > rule.value
  elif op == op_enum.EQUAL:
    return value == rule.value
  else:
    # Unknown operator.
    raise ValueError("Unknown operator: %d" % op)


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


class ForemanClientRuleSet(rdf_structs.RDFProtoStruct):
  """This proto holds rules and the strategy used to evaluate them."""

  protobuf = jobs_pb2.ForemanClientRuleSet
  rdf_deps = [
      ForemanClientRule,
  ]


def ValidateForemanRuleSet(rule_set: jobs_pb2.ForemanClientRuleSet):
  """Validates the rule set."""
  for rule in rule_set.rules:
    if not rule.HasField("rule_type"):
      raise ValueError("Foreman rule has no type set.")

    if rule.rule_type == jobs_pb2.ForemanClientRule.Type.OS:
      pass
    elif rule.rule_type == jobs_pb2.ForemanClientRule.Type.LABEL:
      pass
    elif rule.rule_type == jobs_pb2.ForemanClientRule.Type.REGEX:
      if rule.regex.field == ForemanRegexClientRule.ForemanStringField.UNSET:
        raise ValueError("ForemanRegexClientRule rule invalid - field not set.")
    elif rule.rule_type == jobs_pb2.ForemanClientRule.Type.INTEGER:
      if (
          rule.integer.field
          == ForemanIntegerClientRule.ForemanIntegerField.UNSET
      ):
        raise ValueError(
            "ForemanIntegerClientRule rule invalid - field not set."
        )
    else:
      raise ValueError("Foreman rule has an unknown type set.")


def EvaluateForemanRuleSet(
    rule_set: jobs_pb2.ForemanClientRuleSet,
    client_info: objects_pb2.ClientFullInfo,
) -> bool:
  """Evaluates a ForemanClientRuleSet against client information.

  Args:
    rule_set: The `ForemanClientRuleSet` proto to evaluate.
    client_info: A `ClientFullInfo` instance containing client data.

  Returns:
    True if the client information matches the criteria defined in the rule set,
    False otherwise.

  Raises:
    ValueError: If an unknown match mode or rule type is encountered.
  """
  if rule_set.match_mode == jobs_pb2.ForemanClientRuleSet.MatchMode.MATCH_ALL:
    quantifier = all
  elif rule_set.match_mode == jobs_pb2.ForemanClientRuleSet.MatchMode.MATCH_ANY:
    quantifier = any
  else:
    raise ValueError("Unexpected match mode value: %s" % rule_set.match_mode)

  evals: list[bool] = []
  for rule in rule_set.rules:
    if rule.rule_type == jobs_pb2.ForemanClientRule.Type.OS:
      evals.append(EvaluateForemanOsClientRule(rule.os, client_info))
    elif rule.rule_type == jobs_pb2.ForemanClientRule.Type.LABEL:
      evals.append(EvaluateForemanLabelClientRule(rule.label, client_info))
    elif rule.rule_type == jobs_pb2.ForemanClientRule.Type.REGEX:
      evals.append(EvaluateForemanRegexClientRule(rule.regex, client_info))
    elif rule.rule_type == jobs_pb2.ForemanClientRule.Type.INTEGER:
      evals.append(EvaluateForemanIntegerClientRule(rule.integer, client_info))
    else:
      raise ValueError("Foreman rule has an unknown type set.")

  return quantifier(evals)


class ForemanRule(rdf_structs.RDFProtoStruct):
  """A Foreman rule RDF value."""

  protobuf = jobs_pb2.ForemanRule
  rdf_deps = [
      ForemanClientRuleSet,
      ForemanRuleAction,
      rdfvalue.RDFDatetime,
  ]

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

  def GetLifetime(self):
    if self.expiration_time < self.creation_time:
      raise ValueError("Rule expires before it was created.")
    return self.expiration_time - self.creation_time


def ValidateForemanCondition(condition: jobs_pb2.ForemanCondition) -> None:
  """Validates a ForemanCondition proto."""
  return ValidateForemanRuleSet(condition.client_rule_set)


def EvaluateForemanCondition(
    condition: jobs_pb2.ForemanCondition,
    client_data: objects_pb2.ClientFullInfo,
) -> bool:
  """Evaluates a rule on a client."""
  return EvaluateForemanRuleSet(condition.client_rule_set, client_data)
