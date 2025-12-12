#!/usr/bin/env python
"""A module with implementation of the in-memory keystore."""

from collections.abc import Sequence
import itertools
import os

from grr_response_server.keystore import abstract


class MemKeystore(abstract.Keystore):
  """An in-memory keystore implementation based on a dict."""

  def __init__(self, key_names: Sequence[str]) -> None:
    """Initializes the in-memory keystore.

    Args:
      key_names: A mapping from key names to key material.
    """
    self._keys = {key_name: os.urandom(32) for key_name in key_names}

  def Crypter(self, name: str) -> "XorCrypter":
    """Creates a crypter for the given key to encrypt and decrypt data."""
    try:
      key = self._keys[name]
    except KeyError as error:
      raise abstract.UnknownKeyError(name) from error

    return XorCrypter(key)

  def MAC(self, name: str) -> "XorMAC":
    """Creates a MAC for the given key to sign and verify data."""
    try:
      key = self._keys[name]
    except KeyError as error:
      raise abstract.UnknownKeyError(name) from error

    return XorMAC(key)


class XorCrypter(abstract.Crypter):
  """A simple crypter using XOR cipher.

  Note that this class is indented only for test purposes and should not be used
  for any production code as it does not provide any security [1].

  [1]: https://en.wikipedia.org/wiki/XOR_cipher#Use_and_security
  """

  def __init__(self, key: bytes) -> None:
    """Initializes the crypter.

    Args:
      key: A key used for encrypting data.
    """
    super().__init__()
    self._key = key

  def Encrypt(self, data: bytes, assoc_data: bytes) -> bytes:
    """Encrypts the given data."""
    key = itertools.cycle(self._key)
    return bytes(db ^ kb for db, kb in zip(data + assoc_data, key))

  def Decrypt(self, data: bytes, assoc_data: bytes) -> bytes:
    """Decrypts the given encrypted data."""
    key = itertools.cycle(self._key)

    unencrypted_data = bytes(db ^ kb for db, kb in zip(data, key))
    if unencrypted_data[-len(assoc_data) :] != assoc_data:
      raise abstract.DecryptionError("Incorrect associated data")

    return unencrypted_data[: -len(assoc_data)]


class XorMAC(abstract.MAC):
  """A simple MAC using XOR cipher.

  Note that this class is intended only for test purposes and should not be used
  for any production code as it does not provide any security [1].

  [1]: https://en.wikipedia.org/wiki/XOR_cipher#Use_and_security
  """

  def __init__(self, key: bytes) -> None:
    """Initializes the MAC.

    Args:
      key: A key used for encrypting data.
    """
    super().__init__()
    self._key = key

  def ComputeMAC(self, data: bytes) -> bytes:
    key = itertools.cycle(self._key)
    return bytes(db ^ kb for db, kb in zip(data, key))

  def VerifyMAC(self, mac_value: bytes, data: bytes) -> None:
    expected_mac = self.ComputeMAC(data)
    if mac_value != expected_mac:
      raise abstract.MACVerificationError("Incorrect MAC")
