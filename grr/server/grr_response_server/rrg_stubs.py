#!/usr/bin/env python
"""Stubs for calling RRG actions."""

from typing import Generic, Protocol, Type, TypeVar

from google.protobuf import any_pb2
from google.protobuf import empty_pb2
from google.protobuf import message as pb_message
from grr_response_server import flow_base
from grr_response_server import flow_responses
from grr_response_proto import rrg_pb2
from grr_response_proto.rrg.action import execute_signed_command_pb2 as rrg_execute_signed_command_pb2
from grr_response_proto.rrg.action import get_file_contents_pb2 as rrg_get_file_contents_pb2
from grr_response_proto.rrg.action import get_file_metadata_pb2 as rrg_get_file_metadata_pb2
from grr_response_proto.rrg.action import get_file_sha256_pb2 as rrg_get_file_sha256_pb2
from grr_response_proto.rrg.action import get_filesystem_timeline_pb2 as rrg_get_filesystem_timeline_pb2
from grr_response_proto.rrg.action import get_system_metadata_pb2 as rrg_get_system_metadata_pb2
from grr_response_proto.rrg.action import get_tcp_response_pb2 as rrg_get_tcp_response_pb2
from grr_response_proto.rrg.action import get_winreg_value_pb2 as rrg_get_winreg_value_pb2
from grr_response_proto.rrg.action import grep_file_contents_pb2 as rrg_grep_file_contents_pb2
from grr_response_proto.rrg.action import list_utmp_users_pb2 as rrg_list_utmp_users_pb2
from grr_response_proto.rrg.action import list_winreg_keys_pb2 as rrg_list_winreg_keys_pb2
from grr_response_proto.rrg.action import list_winreg_values_pb2 as rrg_list_winreg_values_pb2
from grr_response_proto.rrg.action import query_wmi_pb2 as rrg_query_wmi_pb2


class _FlowStateMethod(Protocol):
  """Protocol for a flow state method."""

  __self__: flow_base.FlowBase
  __name__: str

  def __call__(self, responses: flow_responses.Responses[any_pb2.Any]) -> None:
    ...


_Args = TypeVar("_Args", bound=pb_message.Message)


class Action(Generic[_Args]):
  """Stub for an RRG action.

  Attributes:
    args: An instance of the Protocol Buffers message to be used as arguments
      for the action invocation.
    context: Additional key-value pairs to pass the flow state method with
      action responses.
  """

  def __init__(
      self,
      action: "rrg_pb2.Action",
      args_type: Type[_Args],
  ) -> None:
    """Initializes the action stub.

    Args:
      action: Action this stub refers to.
      args_type: Type of the arguments this action operates on.
    """
    self._action = action
    self._args = args_type()
    self._filters: list[rrg_pb2.Filter] = []
    self._context: dict[str, str] = {}

  @property
  def args(self) -> _Args:
    return self._args

  @property
  def context(self) -> dict[str, str]:
    return self._context

  def Call(self, next_state: _FlowStateMethod) -> None:
    next_state.__self__.CallRRG(
        action=self._action,
        args=self._args,
        filters=self._filters,
        next_state=next_state.__name__,
        context=self._context,
    )

  # TODO: Use pythonic wrappers for filters.
  def AddFilter(self) -> rrg_pb2.Filter:
    """Returns a new filter to be used by the action."""
    result = rrg_pb2.Filter()
    self._filters.append(result)
    return result


def GetSystemMetadata() -> Action[rrg_get_system_metadata_pb2.Args]:
  return Action(
      action=rrg_pb2.Action.GET_SYSTEM_METADATA,
      args_type=rrg_get_system_metadata_pb2.Args,
  )


def GetFileMetadata() -> Action[rrg_get_file_metadata_pb2.Args]:
  return Action(
      action=rrg_pb2.Action.GET_FILE_METADATA,
      args_type=rrg_get_file_metadata_pb2.Args,
  )


def GetFileContents() -> Action[rrg_get_file_contents_pb2.Args]:
  return Action(
      action=rrg_pb2.Action.GET_FILE_CONTENTS,
      args_type=rrg_get_file_contents_pb2.Args,
  )


def GetFileSha256() -> Action[rrg_get_file_sha256_pb2.Args]:
  return Action(
      action=rrg_pb2.Action.GET_FILE_SHA256,
      args_type=rrg_get_file_sha256_pb2.Args,
  )


def ListUtmpUsers() -> Action[rrg_list_utmp_users_pb2.Args]:
  return Action(
      action=rrg_pb2.Action.LIST_UTMP_USERS,
      args_type=rrg_list_utmp_users_pb2.Args,
  )


def GetFilesystemTimeline() -> Action[rrg_get_filesystem_timeline_pb2.Args]:
  return Action(
      action=rrg_pb2.Action.GET_FILESYSTEM_TIMELINE,
      args_type=rrg_get_filesystem_timeline_pb2.Args,
  )


def ListInterfaces() -> Action[empty_pb2.Empty]:
  return Action(
      action=rrg_pb2.Action.LIST_INTERFACES,
      args_type=empty_pb2.Empty,
  )


def ListMounts() -> Action[empty_pb2.Empty]:
  return Action(
      action=rrg_pb2.Action.LIST_MOUNTS,
      args_type=empty_pb2.Empty,
  )


def GetWinregValue() -> Action[rrg_get_winreg_value_pb2.Args]:
  return Action(
      action=rrg_pb2.Action.GET_WINREG_VALUE,
      args_type=rrg_get_winreg_value_pb2.Args,
  )


def ListWinregValues() -> Action[rrg_list_winreg_values_pb2.Args]:
  return Action(
      action=rrg_pb2.Action.LIST_WINREG_VALUES,
      args_type=rrg_list_winreg_values_pb2.Args,
  )


def ListWinregKeys() -> Action[rrg_list_winreg_keys_pb2.Args]:
  return Action(
      action=rrg_pb2.Action.LIST_WINREG_KEYS,
      args_type=rrg_list_winreg_keys_pb2.Args,
  )


def QueryWmi() -> Action[rrg_query_wmi_pb2.Args]:
  return Action(
      action=rrg_pb2.Action.QUERY_WMI,
      args_type=rrg_query_wmi_pb2.Args,
  )


def GrepFileContents() -> Action[rrg_grep_file_contents_pb2.Args]:
  return Action(
      action=rrg_pb2.Action.GREP_FILE_CONTENTS,
      args_type=rrg_grep_file_contents_pb2.Args,
  )


def GetTcpResponse() -> Action[rrg_get_tcp_response_pb2.Args]:
  return Action(
      action=rrg_pb2.Action.GET_TCP_RESPONSE,
      args_type=rrg_get_tcp_response_pb2.Args,
  )


def ExecuteSignedCommand() -> Action[rrg_execute_signed_command_pb2.Args]:
  return Action(
      action=rrg_pb2.Action.EXECUTE_SIGNED_COMMAND,
      args_type=rrg_execute_signed_command_pb2.Args,
  )
