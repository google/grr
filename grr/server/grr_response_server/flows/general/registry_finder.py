#!/usr/bin/env python
"""Registry finder implementation."""

from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import flows_pb2
from grr_response_server import flow_base
from grr_response_server.flows.general import file_finder


class RegistryFinderCondition(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.RegistryFinderCondition
  rdf_deps = [
      rdf_file_finder.FileFinderContentsLiteralMatchCondition,
      rdf_file_finder.FileFinderContentsRegexMatchCondition,
      rdf_file_finder.FileFinderModificationTimeCondition,
      rdf_file_finder.FileFinderSizeCondition,
  ]


class RegistryFinderArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.RegistryFinderArgs
  rdf_deps = [
      rdf_paths.GlobExpression,
      RegistryFinderCondition,
  ]


def _ConditionsToFileFinderConditions(conditions):
  """Converts FileFinderSizeConditions to RegistryFinderConditions."""
  ff_condition_type_cls = rdf_file_finder.FileFinderCondition.Type
  result = []
  for c in conditions:
    if c.condition_type == RegistryFinderCondition.Type.MODIFICATION_TIME:
      result.append(
          rdf_file_finder.FileFinderCondition(
              condition_type=ff_condition_type_cls.MODIFICATION_TIME,
              modification_time=c.modification_time,
          )
      )
    elif c.condition_type == RegistryFinderCondition.Type.VALUE_LITERAL_MATCH:
      result.append(
          rdf_file_finder.FileFinderCondition(
              condition_type=ff_condition_type_cls.CONTENTS_LITERAL_MATCH,
              contents_literal_match=c.value_literal_match,
          )
      )
    elif c.condition_type == RegistryFinderCondition.Type.VALUE_REGEX_MATCH:
      result.append(
          rdf_file_finder.FileFinderCondition(
              condition_type=ff_condition_type_cls.CONTENTS_REGEX_MATCH,
              contents_regex_match=c.value_regex_match,
          )
      )
    elif c.condition_type == RegistryFinderCondition.Type.SIZE:
      result.append(
          rdf_file_finder.FileFinderCondition(
              condition_type=ff_condition_type_cls.SIZE, size=c.size
          )
      )
    else:
      raise ValueError("Unknown condition type: %s" % c.condition_type)

  return result


class LegacyRegistryFinder(flow_base.FlowBase):
  """This flow looks for registry items matching given criteria.

  TODO: remove by EOY2024.

  This flow is scheduled for removal and is no longer tested (all registry
  finder related tests are using the ClientRegistryFinder or RegistryFinder,
  which is now an alias to ClientRegistryFinder).
  """

  friendly_name = "Legacy Registry Finder (deprecated)"
  category = "/Registry/"
  args_type = RegistryFinderArgs
  behaviours = flow_base.BEHAVIOUR_DEBUG

  @classmethod
  def GetDefaultArgs(cls, username=None):
    del username
    return cls.args_type(
        keys_paths=[
            "HKEY_USERS/%%users.sid%%/Software/"
            "Microsoft/Windows/CurrentVersion/Run/*"
        ]
    )

  def Start(self):
    self.CallFlow(
        file_finder.LegacyFileFinder.__name__,
        flow_args=rdf_file_finder.FileFinderArgs(
            paths=self.args.keys_paths,
            pathtype=rdf_paths.PathSpec.PathType.REGISTRY,
            conditions=_ConditionsToFileFinderConditions(self.args.conditions),
            action=rdf_file_finder.FileFinderAction.Stat(),
        ),
        next_state=self.Done.__name__,
    )

  def Done(self, responses):
    if not responses.success:
      raise flow_base.FlowError("Registry search failed %s" % responses.status)

    for response in responses:
      self.SendReply(response)


class ClientRegistryFinder(flow_base.FlowBase):
  """This flow looks for registry items matching given criteria."""

  friendly_name = "Client Side Registry Finder"
  category = "/Registry/"
  args_type = RegistryFinderArgs
  behaviours = flow_base.BEHAVIOUR_ADVANCED

  @classmethod
  def GetDefaultArgs(cls, username=None):
    del username
    return cls.args_type(
        keys_paths=["HKEY_LOCAL_MACHINE/SOFTWARE/Microsoft/Windows NT/*"]
    )

  def Start(self):
    self.CallFlow(
        file_finder.ClientFileFinder.__name__,
        flow_args=rdf_file_finder.FileFinderArgs(
            paths=self.args.keys_paths,
            pathtype=rdf_paths.PathSpec.PathType.REGISTRY,
            conditions=_ConditionsToFileFinderConditions(self.args.conditions),
            action=rdf_file_finder.FileFinderAction.Stat(),
        ),
        next_state=self.Done.__name__,
    )

  def Done(self, responses):
    if not responses.success:
      raise flow_base.FlowError("Registry search failed %s" % responses.status)

    for response in responses:
      self.SendReply(response)


class RegistryFinder(ClientRegistryFinder):
  """Legacy alias for ClientRegistryFinder."""

  friendly_name = "Registry Finder"
  behaviours = flow_base.BEHAVIOUR_DEBUG
