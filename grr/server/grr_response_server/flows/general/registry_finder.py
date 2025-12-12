#!/usr/bin/env python
"""Registry finder implementation."""

from collections.abc import Iterable
import stat

from google.protobuf import any_pb2
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_server import flow_base
from grr_response_server import flow_responses
from grr_response_server import rrg_stubs
from grr_response_server import rrg_winreg
from grr_response_server.flows.general import file_finder
from grr_response_proto.rrg import os_pb2 as rrg_os_pb2
from grr_response_proto.rrg import winreg_pb2 as rrg_winreg_pb2
from grr_response_proto.rrg.action import list_winreg_values_pb2 as rrg_list_winreg_values_pb2


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


def _ConditionsToFileFinderConditions(
    conditions: Iterable[flows_pb2.RegistryFinderCondition],
) -> list[flows_pb2.FileFinderCondition]:
  """Converts FileFinderSizeConditions to RegistryFinderConditions."""
  result = []
  for c in conditions:
    if (
        c.condition_type
        == flows_pb2.RegistryFinderCondition.Type.MODIFICATION_TIME
    ):
      result.append(
          flows_pb2.FileFinderCondition(
              condition_type=flows_pb2.FileFinderCondition.Type.MODIFICATION_TIME,
              modification_time=c.modification_time,
          )
      )
    elif (
        c.condition_type
        == flows_pb2.RegistryFinderCondition.Type.VALUE_LITERAL_MATCH
    ):
      result.append(
          flows_pb2.FileFinderCondition(
              condition_type=flows_pb2.FileFinderCondition.Type.CONTENTS_LITERAL_MATCH,
              contents_literal_match=c.value_literal_match,
          )
      )
    elif (
        c.condition_type
        == flows_pb2.RegistryFinderCondition.Type.VALUE_REGEX_MATCH
    ):
      result.append(
          flows_pb2.FileFinderCondition(
              condition_type=flows_pb2.FileFinderCondition.Type.CONTENTS_REGEX_MATCH,
              contents_regex_match=c.value_regex_match,
          )
      )
    elif c.condition_type == flows_pb2.RegistryFinderCondition.Type.SIZE:
      result.append(
          flows_pb2.FileFinderCondition(
              condition_type=flows_pb2.FileFinderCondition.Type.SIZE,
              size=c.size,
          )
      )
    else:
      raise ValueError("Unknown condition type: %s" % c.condition_type)

  return result


class ClientRegistryFinder(
    flow_base.FlowBase[
        flows_pb2.RegistryFinderArgs,
        flows_pb2.DefaultFlowStore,
        flows_pb2.DefaultFlowProgress,
    ]
):
  """This flow looks for registry items matching given criteria."""

  friendly_name = "Client Side Registry Finder"
  category = "/Registry/"
  args_type = RegistryFinderArgs
  behaviours = flow_base.BEHAVIOUR_ADVANCED

  proto_args_type = flows_pb2.RegistryFinderArgs
  proto_result_types = (flows_pb2.FileFinderResult,)

  only_protos_allowed = True

  @classmethod
  def GetDefaultArgs(cls, username=None):
    del username
    return cls.args_type(
        keys_paths=["HKEY_LOCAL_MACHINE/SOFTWARE/Microsoft/Windows NT/*"]
    )

  def Start(self):
    if self.rrg_support and all(
        cond.condition_type
        in [
            flows_pb2.RegistryFinderCondition.VALUE_LITERAL_MATCH,
            flows_pb2.RegistryFinderCondition.VALUE_REGEX_MATCH,
            # TODO: Add support for other condition types.
        ]
        for cond in self.proto_args.conditions
    ):
      return self._StartRRG()

    self.CallFlowProto(
        file_finder.ClientFileFinder.__name__,
        flow_args=flows_pb2.FileFinderArgs(
            paths=self.proto_args.keys_paths,
            pathtype=jobs_pb2.PathSpec.PathType.REGISTRY,
            conditions=_ConditionsToFileFinderConditions(
                self.proto_args.conditions
            ),
            action=flows_pb2.FileFinderAction(
                action_type=flows_pb2.FileFinderAction.Action.STAT
            ),
        ),
        next_state=self.Done.__name__,
    )

  def _StartRRG(self):
    if self.rrg_os_type != rrg_os_pb2.Type.WINDOWS:
      raise flow_base.FlowError(f"Non-Windows endpoint: {self.rrg_os_type}")

    for key in self.proto_args.keys_paths:
      list_winreg_values = rrg_stubs.ListWinregValues()

      try:
        hkey, key = key.split("\\", 1)
      except ValueError as error:
        raise flow_base.FlowError(
            f"Invalid registry key: {key}",
        ) from error

      try:
        list_winreg_values.args.root = rrg_winreg.HKEY_ENUM[hkey]
      except KeyError as error:
        raise flow_base.FlowError(
            f"Unexpected root key: {hkey}",
        ) from error

      key_glob = rrg_winreg.KeyGlob(key)

      list_winreg_values.args.key = key_glob.root
      list_winreg_values.args.max_depth = key_glob.root_level

      # Because walking can return excessive entries, we use RRG filters to skip
      # those keys that do not match the glob exactly.
      key_glob_cond = list_winreg_values.AddFilter().conditions.add()
      key_glob_cond.string_match = key_glob.regex.pattern
      key_glob_cond.field.extend([
          rrg_list_winreg_values_pb2.Result.KEY_FIELD_NUMBER,
      ])

      for cond in self.proto_args.conditions:
        # TODO: Simplify condition creation with wrappers.
        rrg_filter = list_winreg_values.AddFilter()

        if cond.condition_type == cond.VALUE_LITERAL_MATCH:
          cond_literal = cond.value_literal_match.literal
          cond_literal_str = cond_literal.decode("utf-8", "backslashreplace")

          # We don't know what the type of the returned value is, so we add
          # multiple conditions that can match.

          rrg_cond_bytes = rrg_filter.conditions.add()
          rrg_cond_bytes.field.extend([
              rrg_list_winreg_values_pb2.Result.VALUE_FIELD_NUMBER,
              rrg_winreg_pb2.Value.BYTES_FIELD_NUMBER,
          ])
          rrg_cond_bytes.bytes_equal = cond_literal

          rrg_cond_str = rrg_filter.conditions.add()
          rrg_cond_str.field.extend([
              rrg_list_winreg_values_pb2.Result.VALUE_FIELD_NUMBER,
              rrg_winreg_pb2.Value.STRING_FIELD_NUMBER,
          ])
          rrg_cond_str.string_equal = cond_literal_str

          rrg_cond_expand_str = rrg_filter.conditions.add()
          rrg_cond_expand_str.field.extend([
              rrg_list_winreg_values_pb2.Result.VALUE_FIELD_NUMBER,
              rrg_winreg_pb2.Value.EXPAND_STRING_FIELD_NUMBER,
          ])
          rrg_cond_expand_str.string_equal = cond_literal_str

        elif cond.condition_type == cond.VALUE_REGEX_MATCH:
          cond_regex = cond.value_regex_match.regex
          cond_regex_str = cond_regex.decode("utf-8", "backslashreplace")

          # We don't know what the type of the returned value is, so we add
          # multiple conditions that can match.

          rrg_cond_bytes = rrg_filter.conditions.add()
          rrg_cond_bytes.field.extend([
              rrg_list_winreg_values_pb2.Result.VALUE_FIELD_NUMBER,
              rrg_winreg_pb2.Value.BYTES_FIELD_NUMBER,
          ])
          rrg_cond_bytes.bytes_match = cond_regex_str

          rrg_cond_str = rrg_filter.conditions.add()
          rrg_cond_str.field.extend([
              rrg_list_winreg_values_pb2.Result.VALUE_FIELD_NUMBER,
              rrg_winreg_pb2.Value.STRING_FIELD_NUMBER,
          ])
          rrg_cond_str.string_match = cond_regex_str

          rrg_cond_expand_str = rrg_filter.conditions.add()
          rrg_cond_expand_str.field.extend([
              rrg_list_winreg_values_pb2.Result.VALUE_FIELD_NUMBER,
              rrg_winreg_pb2.Value.EXPAND_STRING_FIELD_NUMBER,
          ])
          rrg_cond_expand_str.string_match = cond_regex_str

        else:
          raise ValueError(f"Unsupported condtion type: {cond.condition_type}")

      list_winreg_values.Call(self._ProcessRRGListWinregValues)

  @flow_base.UseProto2AnyResponses
  def _ProcessRRGListWinregValues(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    if not responses.success:
      self.Log("Listing key values failed: {}", responses.status)
      return

    for response_any in responses:
      response = rrg_list_winreg_values_pb2.Result()
      response.ParseFromString(response_any.value)

      result = flows_pb2.FileFinderResult()
      result.stat_entry.CopyFrom(rrg_winreg.StatEntryOfValueResult(response))
      # Because we only use `list_winreg_values` and don't do `list_winreg_keys`
      # we mark entry for the default value as directory.
      if not response.value.name:
        result.stat_entry.st_mode |= stat.S_IFDIR

      self.SendReplyProto(result)

  @flow_base.UseProto2AnyResponses
  def Done(self, responses: flow_responses.Responses[any_pb2.Any]) -> None:
    if not responses.success:
      raise flow_base.FlowError("Registry search failed %s" % responses.status)

    for response_any in responses:
      unpacked_response = flows_pb2.FileFinderResult()
      unpacked_response.ParseFromString(response_any.value)
      self.SendReplyProto(unpacked_response)


class RegistryFinder(ClientRegistryFinder):
  """Legacy alias for ClientRegistryFinder."""

  friendly_name = "Registry Finder"
  behaviours = flow_base.BEHAVIOUR_DEBUG
