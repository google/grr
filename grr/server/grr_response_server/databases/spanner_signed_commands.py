#!/usr/bin/env python
"""A module with signed command methods of the Spanner database implementation."""
import base64

from typing import Sequence

from google.api_core.exceptions import AlreadyExists, InvalidArgument, NotFound
from google.cloud import spanner as spanner_lib

from grr_response_core.lib.util import iterator
from grr_response_proto import signed_commands_pb2
from grr_response_server.databases import db
from grr_response_server.databases import db_utils
from grr_response_server.databases import spanner_utils


class SignedCommandsMixin:
  """A Spanner database mixin with implementation of signed command methods."""

  db: spanner_utils.Database

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def WriteSignedCommands(
      self,
      signed_commands: Sequence[signed_commands_pb2.SignedCommand],
  ) -> None:
    """Writes a signed command to the database."""
    def Mutation(mut) -> None:
      for signed_command in signed_commands:
        mut.insert(
          table="SignedCommands",
          columns=("Id", "OperatingSystem", "Ed25519Signature", "Command"),
          values=[(
                   signed_command.id,
                   signed_command.operating_system,
                   base64.b64encode(bytes(signed_command.ed25519_signature)),
                   base64.b64encode(bytes(signed_command.command))
                  )]
        )

    try:
      self.db.Mutate(Mutation, txn_tag="WriteSignedCommand")
    except AlreadyExists as e:
      raise db.AtLeastOneDuplicatedSignedCommandError(signed_commands) from e
    except InvalidArgument as e:
      raise db.AtLeastOneDuplicatedSignedCommandError(signed_commands) from e


  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadSignedCommand(
      self,
      id_: str,
      operating_system: signed_commands_pb2.SignedCommand.OS,
  ) -> signed_commands_pb2.SignedCommand:
    """Reads signed command from the database."""
    params = {}
    query = """
      SELECT
        c.Id, c.Ed25519Signature, c.Command
      FROM SignedCommands AS c
      WHERE
        c.Id = {id}
      AND
        c.OperatingSystem = {operating_system}
    """
    params["id"] = id_
    params["operating_system"] = operating_system

    try:
      (
          id_,
          ed25519_signature,
          command_bytes,
      ) = self.db.ParamQuerySingle(query, params, txn_tag="ReadSignedCommand")
    except NotFound as ex:
      raise db.NotFoundError() from ex

    signed_command = signed_commands_pb2.SignedCommand()
    signed_command.id = id_
    signed_command.operating_system = operating_system
    signed_command.ed25519_signature = base64.b64decode(ed25519_signature)
    signed_command.command = base64.b64decode(command_bytes)

    return signed_command

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadSignedCommands(
      self,
  ) -> Sequence[signed_commands_pb2.SignedCommand]:
    """Reads signed command from the database."""
    query = """
      SELECT
        c.Id, c.OperatingSystem, c.Ed25519Signature, c.Command
      FROM
        SignedCommands AS c
    """
    signed_commands = []
    for (
        command_id,
        operating_system,
        signature,
        command_bytes,
    ) in self.db.Query(query, txn_tag="ReadSignedCommand"):

      signed_command = signed_commands_pb2.SignedCommand()
      signed_command.id = command_id
      signed_command.operating_system = operating_system
      signed_command.ed25519_signature = base64.b64decode(signature)
      signed_command.command = base64.b64decode(command_bytes)

      signed_commands.append(signed_command)

    return signed_commands

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def DeleteAllSignedCommands(
      self,
  ) -> None:
    """Deletes all signed command from the database."""
    to_delete = self.ReadSignedCommands()
    if not to_delete:
      return

    def Mutation(mut) -> None:
      for command in to_delete:
        mut.delete("SignedCommands", spanner_lib.KeySet(keys=[[command.id, int(command.operating_system)]]))

    self.db.Mutate(Mutation, txn_tag="DeleteAllSignedCommands")