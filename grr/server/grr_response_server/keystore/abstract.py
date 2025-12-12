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

  @abc.abstractmethod
  def MAC(self, name: str) -> "MAC":
    """Creates a MAC for the given key to sign and verify data.

    Args:
      name: A name of the key to create the MAC for.

    Returns:
      A MAC instance.
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


class MAC(metaclass=abc.ABCMeta):
  """A message authentication code interface."""

  @abc.abstractmethod
  def ComputeMAC(self, data: bytes) -> bytes:
    """Computes the message authentication code (MAC) for data.

    Args:
      data: bytes, the input data.

    Returns:
      The resulting MAC as bytes.
    """

  @abc.abstractmethod
  def VerifyMAC(self, mac_value: bytes, data: bytes) -> None:
    """Verifies if mac is a correct authentication code (MAC) for data.

    Args:
      mac_value: bytes. The mac to be checked.
      data: bytes. The data to be checked.

    Raises:
      MACVerificationError: If the MAC is not valid.
    """


class UnknownKeyError(Exception):
  """An error class for situations when a key is not know."""

  def __init__(self, key_name: str) -> None:
    super().__init__(f"Unknown key: '{key_name}'")
    self.key_name = key_name


class DecryptionError(Exception):
  """An error class for situation when decryption failed."""


class MACVerificationError(Exception):
  """An error class for situation when MAC verification failed."""
