#!/usr/bin/env python
"""An abstract command signer."""

import abc


class CommandSignatureValidationError(Exception):
  """An exception class raised when a command signature is invalid."""


class AbstractCommandSigner(metaclass=abc.ABCMeta):
  """A base class for command signers."""

  @abc.abstractmethod
  def Sign(self, command_bytes: bytes) -> bytes:
    """Signs a command and returns the signature."""

  @abc.abstractmethod
  def Verify(self, signature: bytes, command: bytes) -> None:
    """Validates a signature for given data with a verification key.

    Args:
      signature: Signature to verify.
      command: Serialized command that was signed.

    Raises:
      CommandSignatureValidationError: Invalid signature
    """
