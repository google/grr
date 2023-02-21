#!/usr/bin/env python
"""A module with the definition of the abstract keystore."""
import abc


class Keystore(metaclass=abc.ABCMeta):
  """A keystore interface."""

  @abc.abstractmethod
  def Crypter(self, name: str) -> "Crypter":
    """Creates a crypter for the given key to encrypt and decrypt data.

    Args:
      name: A name of the key to create the crypter for.

    Returns:
      A crypter instance.
    """


class Crypter(metaclass=abc.ABCMeta):
  """A crypter interface."""

  @abc.abstractmethod
  def Encrypt(self, data: bytes, assoc_data: bytes) -> bytes:
    """Encrypts the given data.

    Args:
      data: Data to encrypt.
      assoc_data: Associated data used for authenticating encryption.

    Returns:
      An encrypted blob of data.
    """

  @abc.abstractmethod
  def Decrypt(self, data: bytes, assoc_data: bytes) -> bytes:
    """Decrypts the given encrypted data.

    Args:
      data: Encrypted data to decrypt.
      assoc_data: Associated data used for authenticating decryption.

    Returns:
      A decrypted blob of data.

    Raises:
        DecryptionError: If it is not possible to decrypt the given data.
    """


class UnknownKeyError(Exception):
  """An error class for situations when a key is not know."""

  def __init__(self, key_name: str) -> None:
    super().__init__(f"Unknown key: '{key_name}'")
    self.key_name = key_name


class DecryptionError(Exception):
  """An error class for situation when decryption failed."""
