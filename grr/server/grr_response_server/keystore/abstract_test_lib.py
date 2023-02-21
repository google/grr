#!/usr/bin/env python
"""Common utilities for testing keystore implementations."""
import abc
from typing import Sequence

from grr_response_server.keystore import abstract


class KeystoreTestMixin(metaclass=abc.ABCMeta):
  """A mixin class with keystore test suite."""

  @abc.abstractmethod
  def CreateKeystore(self, key_names: Sequence[str]) -> abstract.Keystore:
    """Creates a keystore instance with the specified key set.

    Args:
      key_names: A sequence of key names that should be available in the created
        keystore.

    Returns:
      A keystore instance with the specified key set.
    """

  # This is a mixin class, we have to make Pytype forget about missing assertion
  # methods.
  # pytype: disable=attribute-error

  # Test methods do not require docstrings (but pylint is not aware that these
  # are actually test methods).
  # pylint: disable=missing-function-docstring

  def testCrypterRaisesOnUnknownKey(self):
    keystore = self.CreateKeystore([])

    with self.assertRaises(abstract.UnknownKeyError) as context:
      keystore.Crypter("foobar")

    self.assertEqual(context.exception.key_name, "foobar")

  def testCrypterEncryptsAndDecryptsSingleKey(self):
    keystore = self.CreateKeystore(["foo"])

    crypter = keystore.Crypter("foo")

    data = b"\xBB\xAA\x55"

    encrypted_data = crypter.Encrypt(data, b"assoc_data")
    self.assertNotEqual(data, encrypted_data)

    decrypted_data = crypter.Decrypt(encrypted_data, b"assoc_data")
    self.assertEqual(decrypted_data, data)

  def testCrypterEncryptsAndDecryptsMultipleKeys(self):
    keystore = self.CreateKeystore(["foo", "bar"])

    crypter_foo = keystore.Crypter("foo")
    crypter_bar = keystore.Crypter("bar")

    data = b"\xBB\xAA\x55"

    encrypted_data_foo = crypter_foo.Encrypt(data, b"assoc_data")
    encrypted_data_bar = crypter_bar.Encrypt(data, b"assoc_data")
    self.assertNotEqual(data, encrypted_data_foo)
    self.assertNotEqual(data, encrypted_data_bar)
    self.assertNotEqual(encrypted_data_foo, encrypted_data_bar)

    decrypted_data_foo = crypter_foo.Decrypt(encrypted_data_foo, b"assoc_data")
    decrypted_data_bar = crypter_bar.Decrypt(encrypted_data_bar, b"assoc_data")
    self.assertEqual(decrypted_data_foo, data)
    self.assertEqual(decrypted_data_bar, data)

  def testCrypterDecryptionError(self):
    crypter = self.CreateKeystore(["foo"]).Crypter("foo")

    data = b"\xBB\xAA\x55"
    encrypted_data = crypter.Encrypt(data, b"assoc_data")

    with self.assertRaises(abstract.DecryptionError):
      crypter.Decrypt(encrypted_data, b"different_assoc_data")

  # pytype: enable=attribute-error
  # pylint: enable=missing-function-docstring
