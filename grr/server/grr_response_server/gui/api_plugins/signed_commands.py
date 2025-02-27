#!/usr/bin/env python
"""API handlers for signed commands."""

from typing import Optional

from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import signed_commands_pb2
from grr_response_proto.api import signed_commands_pb2 as api_signed_commands_pb2
from grr_response_server import data_store
from grr_response_server.gui import api_call_context
from grr_response_server.gui import api_call_handler_base
from grr_response_server.models import signed_commands as models_signed_commands
from grr_response_proto.rrg.action import execute_signed_command_pb2 as rrg_execute_signed_command_pb2


class ApiEnvVar(rdf_structs.RDFProtoStruct):
  protobuf = api_signed_commands_pb2.ApiEnvVar
  rdf_deps = []


class ApiCommand(rdf_structs.RDFProtoStruct):
  protobuf = api_signed_commands_pb2.ApiCommand
  rdf_deps = [ApiEnvVar]


class ApiSignedCommand(rdf_structs.RDFProtoStruct):
  protobuf = api_signed_commands_pb2.ApiSignedCommand
  rdf_deps = []


class ApiCreateSignedCommandsArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_signed_commands_pb2.ApiCreateSignedCommandsArgs
  rdf_deps = [
      ApiSignedCommand,
  ]


class ApiListSignedCommandsResult(rdf_structs.RDFProtoStruct):
  protobuf = api_signed_commands_pb2.ApiListSignedCommandsResult
  rdf_deps = [
      ApiSignedCommand,
  ]


class ApiCreateSignedCommandsHandler(api_call_handler_base.ApiCallHandler):
  """Handles signed command creation request."""

  args_type = ApiCreateSignedCommandsArgs
  proto_args_type = api_signed_commands_pb2.ApiCreateSignedCommandsArgs

  def Handle(
      self,
      args: api_signed_commands_pb2.ApiCreateSignedCommandsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> None:
    """Handles signed command creation request."""

    commands_to_write = []
    for args_signed_command in args.signed_commands:
      signed_command = signed_commands_pb2.SignedCommand()
      if not args_signed_command.id:
        raise ValueError("Command id is required.")
      if (
          not args_signed_command.HasField("operating_system")
          or args_signed_command.operating_system
          == api_signed_commands_pb2.ApiSignedCommand.OS.UNSET
      ):
        raise ValueError("Command operating system is required.")
      if not args_signed_command.ed25519_signature:
        # TODO: Add signature verification.
        raise ValueError("Command signature is required.")

      rrg_command = rrg_execute_signed_command_pb2.Command()
      rrg_command.ParseFromString(args_signed_command.command)
      if not rrg_command.path.raw_bytes:
        raise ValueError("Command path is required.")
      if not rrg_command.HasField(
          "unsigned_stdin_allowed"
      ) and not rrg_command.HasField("signed_stdin"):
        raise ValueError("Command stdin is required.")

      signed_command.id = args_signed_command.id
      signed_command.operating_system = args_signed_command.operating_system
      signed_command.ed25519_signature = args_signed_command.ed25519_signature
      signed_command.command = args_signed_command.command
      commands_to_write.append(signed_command)

    data_store.REL_DB.WriteSignedCommands(commands_to_write)


class ApiListSignedCommandsHandler(api_call_handler_base.ApiCallHandler):
  """Handles signed command retrieval request."""

  return_type = ApiListSignedCommandsResult
  proto_return_type = api_signed_commands_pb2.ApiListSignedCommandsResult

  def Handle(
      self,
      args: Optional[None] = None,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_signed_commands_pb2.ApiListSignedCommandsResult:
    """Handles signed command retrieval request."""
    signed_commands = data_store.REL_DB.ReadSignedCommands()
    api_signed_commands = [
        models_signed_commands.InitApiSignedCommandFromSignedCommand(
            signed_command
        )
        for signed_command in signed_commands
    ]
    return api_signed_commands_pb2.ApiListSignedCommandsResult(
        signed_commands=api_signed_commands
    )


class ApiDeleteAllSignedCommandsHandler(api_call_handler_base.ApiCallHandler):
  """Handles signed command deletion request."""

  def Handle(
      self,
      args: Optional[None] = None,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> None:
    """Handles signed command deletion request."""
    data_store.REL_DB.DeleteAllSignedCommands()
