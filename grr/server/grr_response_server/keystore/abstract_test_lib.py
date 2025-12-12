#!/usr/bin/env python
"""Common utilities for testing keystore implementations."""

import abc
from collections.abc import Sequence

from grr_response_server.keystore import abstract


class KeystoreTestMixin(metaclass=abc.ABCMeta):
  """A mixin class with keystore test suite."""

  @abc.abstractmethod
  def CreateKeystore(
      self, aead_key_names: Sequence[str], mac_key_names: Sequence[str]
  ) -> abstract.Keystore:
    """Creates a keystore instance with the specified key set.

    Args:
      aead_key_names: A sequence of AEAD key names that should be available in
        the created keystore.
      mac_key_names: A sequence of MAC key names that should be available in the
        created keystore.

    Returns:
      A keystore instance with the specified key set.
    """

  # This is a mixin class, we have to make Pytype forget about missing assertion
  # methods.
  # pytype: disable=attribute-error

  # Test methods do not require docstrings (but pylint is not aware that these
  # are actually test methods).
  # pylint: disable=missing-function-docstring,invalid-name

  def testCrypterRaisesOnUnknownKey(self):
    keystore = self.CreateKeystore(
        aead_key_names=[],
        mac_key_names=[],
    )

    with self.assertRaises(abstract.UnknownKeyError) as context:
      keystore.Crypter("foobar")

    self.assertEqual(context.exception.key_name, "foobar")

  def testCrypterEncryptsAndDecryptsSingleKey(self):
    keystore = self.CreateKeystore(aead_key_names=["foo"], mac_key_names=[])

    crypter = keystore.Crypter("foo")

    data = b"\xBB\xAA\x55"

    encrypted_data = crypter.Encrypt(data, b"assoc_data")
    self.assertNotEqual(data, encrypted_data)

    decrypted_data = crypter.Decrypt(encrypted_data, b"assoc_data")
    self.assertEqual(decrypted_data, data)

  def testCrypterEncryptsAndDecryptsMultipleKeys(self):
    keystore = self.CreateKeystore(
        aead_key_names=["foo", "bar"], mac_key_names=[]
    )

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
    crypter = self.CreateKeystore(
        aead_key_names=["foo"], mac_key_names=[]
    ).Crypter("foo")

    data = b"\xBB\xAA\x55"
    encrypted_data = crypter.Encrypt(data, b"assoc_data")

    with self.assertRaises(abstract.DecryptionError):
      crypter.Decrypt(encrypted_data, b"different_assoc_data")

  def testMACRaisesOnUnknownKey(self):
    keystore = self.CreateKeystore(aead_key_names=[], mac_key_names=[])

    with self.assertRaises(abstract.UnknownKeyError) as context:
      keystore.MAC("foobar")

    self.assertEqual(context.exception.key_name, "foobar")

  def testMACComputesAndVerifiesSingleKey(self):
    keystore = self.CreateKeystore(aead_key_names=[], mac_key_names=["foo"])

    mac = keystore.MAC("foo")

    data = b"\xBB\xAA\x55"

    mac_data = mac.ComputeMAC(data)
    self.assertNotEqual(data, mac_data)

    mac.VerifyMAC(mac_data, data)

  def testMACComputesAndVerifiesMultipleKeys(self):
    keystore = self.CreateKeystore(
        aead_key_names=[],
        mac_key_names=["foo", "bar"],
    )

    mac_foo = keystore.MAC("foo")
    mac_bar = keystore.MAC("bar")

    data = b"\xBB\xAA\x55"

    mac_data_foo = mac_foo.ComputeMAC(data)
    mac_data_bar = mac_bar.ComputeMAC(data)
    self.assertNotEqual(data, mac_data_foo)
    self.assertNotEqual(data, mac_data_bar)
    self.assertNotEqual(mac_data_foo, mac_data_bar)

    mac_foo.VerifyMAC(mac_data_foo, data)
    mac_bar.VerifyMAC(mac_data_bar, data)

  def testMACVerificationError(self):
    mac = self.CreateKeystore(aead_key_names=[], mac_key_names=["foo"]).MAC(
        "foo"
    )

    data = b"\xBB\xAA\x55"
    mac_data = mac.ComputeMAC(data)

    with self.assertRaises(abstract.MACVerificationError):
      mac.VerifyMAC(mac_data, b"different_data")

  # pytype: enable=attribute-error
  # pylint: enable=missing-function-docstring,invalid-name
