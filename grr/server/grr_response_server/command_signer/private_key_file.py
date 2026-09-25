#!/usr/bin/env python
"""A command signer using a private key from a file."""

from typing import IO

import cryptography.exceptions as crypto_exceptions
from cryptography.hazmat.primitives.asymmetric import ed25519

from grr_response_server.command_signer import abstract
from grr_response_proto.rrg.action import execute_signed_command_pb2 as rrg_execute_signed_command_pb2


class PrivateKeyFileCommandSigner(abstract.AbstractCommandSigner):
  """A command signer that uses a private key from a config."""

  @classmethod
  def FromPath(cls, path: str) -> "PrivateKeyFileCommandSigner":
    with open(path, "rb") as file:
      return cls.FromFile(file)

  @classmethod
  def FromFile(cls, file: IO[bytes]) -> "PrivateKeyFileCommandSigner":
    return cls.FromBytes(file.read())

  @classmethod
  def FromBytes(cls, key_bytes: bytes) -> "PrivateKeyFileCommandSigner":
    return cls(ed25519.Ed25519PrivateKey.from_private_bytes(key_bytes))

  def __init__(self, private_key: ed25519.Ed25519PrivateKey):
    self._private_key = private_key
    self._public_key = private_key.public_key()

  def Sign(self, command_bytes: bytes) -> bytes:
    # This is unused, we just want to verify that the bytes really correspond
    # to a command.
    command = rrg_execute_signed_command_pb2.Command()
    command.ParseFromString(command_bytes)

    return self._private_key.sign(command_bytes)

  def Verify(self, signature: bytes, command_bytes: bytes) -> None:
    command = rrg_execute_signed_command_pb2.Command()
    command.ParseFromString(command_bytes)

    try:
      self._public_key.verify(signature, command_bytes)
    except crypto_exceptions.InvalidSignature as e:
      raise abstract.CommandSignatureValidationError(
          "Signature verification failed for command: %s" % command
      ) from e
