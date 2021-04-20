#!/usr/bin/env python
import io
import os

from absl.testing import absltest
from cryptography import exceptions as crypto_exceptions
from cryptography.hazmat.primitives.ciphers import aead as crypto_aead

from grr_response_core.lib.util import aead


class EncryptDecryptTest(absltest.TestCase):

  def testReadWholeEmpty(self):
    self._testReadWhole(b"")

  def testReadWholeSmall(self):
    self._testReadWhole(b"foo")

  def testReadWholeRandom(self):
    self._testReadWhole(os.urandom(128))

  def testReadWholeRandomUneven(self):
    self._testReadWhole(os.urandom(131))

  def testReadWholeRandomLarge(self):
    self._testReadWhole(os.urandom(8 * 1024 * 1024))

  def testReadWholeRandomLargeUneven(self):
    self._testReadWhole(os.urandom(8 * 1024 * 1024 + 9))

  def _testReadWhole(self, data: bytes):  # pylint: disable=invalid-name
    key = os.urandom(32)

    encrypted = aead.Encrypt(io.BytesIO(data), key)
    decrypted = aead.Decrypt(encrypted, key)

    self.assertEqual(decrypted.read(), data)


class EncryptTest(absltest.TestCase):

  def testReadExact(self):
    key = os.urandom(32)
    data = os.urandom(1024)

    encrypted = aead.Encrypt(io.BytesIO(data), key)

    chunk_1 = encrypted.read(1)
    self.assertLen(chunk_1, 1)

    chunk_23 = encrypted.read(23)
    self.assertLen(chunk_23, 23)

    chunk_71 = encrypted.read(71)
    self.assertLen(chunk_71, 71)

    chunk_107 = encrypted.read(107)
    self.assertLen(chunk_107, 107)

    chunk_rest = encrypted.read()

    buf = io.BytesIO(chunk_1 + chunk_23 + chunk_71 + chunk_107 + chunk_rest)
    decrypted = aead.Decrypt(buf, key)

    self.assertEqual(decrypted.read(), data)


class DecryptTest(absltest.TestCase):

  def testReadExact(self):
    count = 2048
    key = os.urandom(32)

    buf = io.BytesIO(b"foobarbazquxnorf" * count)
    encrypted = aead.Encrypt(buf, key)
    decrypted = aead.Decrypt(encrypted, key)

    for _ in range(count):
      self.assertEqual(decrypted.read(3), b"foo")
      self.assertEqual(decrypted.read(3), b"bar")
      self.assertEqual(decrypted.read(3), b"baz")
      self.assertEqual(decrypted.read(3), b"qux")
      self.assertEqual(decrypted.read(4), b"norf")

    self.assertEqual(decrypted.read(), b"")

  def testIncorrectNonceLength(self):
    key = os.urandom(32)

    buf = io.BytesIO()

    nonce = os.urandom(aead._AEAD_NONCE_SIZE - 1)
    buf.write(nonce)
    buf.seek(0, io.SEEK_SET)

    with self.assertRaisesRegex(EOFError, "nonce length"):
      aead.Decrypt(buf, key).read()

  def testIncorrectTag(self):
    key = os.urandom(32)
    aesgcm = crypto_aead.AESGCM(key)

    buf = io.BytesIO()

    nonce = os.urandom(aead._AEAD_NONCE_SIZE)
    buf.write(nonce)
    buf.write(aesgcm.encrypt(nonce, b"foo", b"QUUX"))
    buf.seek(0, io.SEEK_SET)

    with self.assertRaises(crypto_exceptions.InvalidTag):
      aead.Decrypt(buf, key).read()

  def testIncorrectData(self):
    key = os.urandom(32)
    aesgcm = crypto_aead.AESGCM(key)

    buf = io.BytesIO()

    nonce = os.urandom(aead._AEAD_NONCE_SIZE)
    adata = aead._AEAD_ADATA_FORMAT.pack(0, True)
    buf.write(nonce)
    buf.write(aesgcm.encrypt(nonce, b"foo", adata))
    buf.getbuffer()[-1] ^= 0b10101010  # Corrupt last byte.
    buf.seek(0, io.SEEK_SET)

    with self.assertRaises(crypto_exceptions.InvalidTag):
      aead.Decrypt(buf, key).read()


if __name__ == "__main__":
  absltest.main()
