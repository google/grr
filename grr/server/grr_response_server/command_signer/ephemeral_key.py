#!/usr/bin/env python
"""A command signer using a key generated during program execution.

This implementation is in support of https://github.com/google/rrg/issues/137.
It is not intended for any real use of command signing functionality.
"""

import cryptography.exceptions as crypto_exceptions
from cryptography.hazmat.primitives.asymmetric import ed25519

from grr_response_server.command_signer import abstract
from grr_response_proto.rrg.action import execute_signed_command_pb2 as rrg_execute_signed_command_pb2


class EphemeralKeyCommandSigner(abstract.AbstractCommandSigner):
  """A command signer that generates a key during program execution."""

  def __init__(self):
    self._private_key = ed25519.Ed25519PrivateKey.generate()
    self._public_key = self._private_key.public_key()

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
