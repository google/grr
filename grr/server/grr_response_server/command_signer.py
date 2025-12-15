#!/usr/bin/env python
"""An abstract command signer."""

import abc

from grr_response_proto.rrg.action import execute_signed_command_pb2 as rrg_execute_signed_command_pb2


class CommandSignatureValidationError(Exception):
  """An exception class raised when a command signature is invalid."""


class AbstractCommandSigner(metaclass=abc.ABCMeta):
  """A base class for command signers."""

  @abc.abstractmethod
  def Sign(self, command: rrg_execute_signed_command_pb2.Command) -> bytes:
    """Signs a command and returns the signature."""

  @abc.abstractmethod
  def Verify(
      self,
      signature: bytes,
      command: rrg_execute_signed_command_pb2.Command,
  ) -> None:
    """Validates a signature for given data with a verification key.

    Args:
      signature: Signature to verify.
      command: Command that was signed.

    Raises:
      CommandSignatureValidationError: Invalid signature
    """
