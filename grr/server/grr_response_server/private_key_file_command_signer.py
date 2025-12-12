#!/usr/bin/env python
"""A command signer using a private key from a file."""

import cryptography.exceptions as crypto_exceptions
from cryptography.hazmat.primitives.asymmetric import ed25519

from grr_response_core import config
from grr_response_server import command_signer
from grr_response_proto.rrg.action import execute_signed_command_pb2 as rrg_execute_signed_command_pb2


class PrivateKeyFileCommandSigner(command_signer.AbstractCommandSigner):
  """A command signer that uses a private key from a config."""

  def __init__(self):
    key_file = config.CONFIG["CommandSigning.ed25519_private_key_file"]
    if not key_file:
      raise RuntimeError("Private key file not specified")

    with open(key_file, "rb") as f:
      key = f.read()
    self._private_key = ed25519.Ed25519PrivateKey.from_private_bytes(key)
    self._public_key = self._private_key.public_key()

  def Sign(self, command: rrg_execute_signed_command_pb2.Command) -> bytes:
    return self._private_key.sign(command.SerializeToString())

  def Verify(
      self, signature: bytes, command: rrg_execute_signed_command_pb2.Command
  ) -> None:
    try:
      self._public_key.verify(signature, command.SerializeToString())
    except crypto_exceptions.InvalidSignature as e:
      raise command_signer.CommandSignatureValidationError(
          "Signature verification failed for command: %s" % command
      ) from e
