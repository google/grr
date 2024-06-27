#!/usr/bin/env python
"""Crypto rdfvalue tests."""

import binascii
import hashlib
import os
import unittest
from unittest import mock

from absl import app

from grr_response_core import config
from grr_response_core.lib import config_lib
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import type_info
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import crypto as rdf_crypto
from grr_response_core.lib.rdfvalues import test_base as rdf_test_base
from grr_response_proto import jobs_pb2
from grr.test_lib import test_lib


class SignedBlobTest(rdf_test_base.RDFValueTestMixin, test_lib.GRRBaseTest):
  rdfvalue_class = rdf_crypto.SignedBlob

  def setUp(self):
    super().setUp()
    self.private_key = config.CONFIG[
        "PrivateKeys.executable_signing_private_key"
    ]
    self.public_key = config.CONFIG["Client.executable_signing_public_key"]

  def GenerateSample(self, number=0):
    result = self.rdfvalue_class()
    result.Sign(("Sample %s" % number).encode("ascii"), self.private_key)

    return result

  @unittest.skip(
      "Samples are expected to be different for the same data as PSS padding"
      " generates a new Hash for every sample."
  )
  def testComparisons(self):
    pass

  def testSignVerify(self):
    sample = self.GenerateSample()

    self.assertTrue(sample.Verify(self.public_key))

    # Change the data - this should fail since the hash is incorrect.
    sample.data += b"X"
    self.assertRaises(
        rdf_crypto.VerificationError, sample.Verify, self.public_key
    )

    # Update the hash
    sample.digest = hashlib.sha256(sample.data).digest()

    # Should still fail.
    self.assertRaises(
        rdf_crypto.VerificationError, sample.Verify, self.public_key
    )

    # If we change the digest verification should fail.
    sample = self.GenerateSample()
    sample.digest_type = sample.HashType.MD5

    self.assertRaises(rdfvalue.DecodeError, sample.Verify, self.public_key)

    # PSS should be accepted.
    sample = self.GenerateSample()
    sample.signature_type = sample.SignatureType.RSA_PSS
    sample.signature = self.private_key.Sign(sample.data)
    sample.Verify(self.public_key)


class CryptoTestBase(test_lib.GRRBaseTest):
  """Base class for all crypto tests here."""


class TestCryptoTypeInfos(CryptoTestBase):
  """Test that invalid configuration types are rejected.

  There is no need to check for success here because if that did not work we
  would not be able to run any tests.
  """

  def setUp(self):
    super().setUp()
    config_stubber = test_lib.PreserveConfig()
    config_stubber.Start()
    self.addCleanup(config_stubber.Stop)

  def testInvalidRSAPrivateKey(self):
    """Deliberately try to parse invalid RSA keys."""
    config.CONFIG.Initialize(data="""
[PrivateKeys]
executable_signing_private_key = -----BEGIN RSA PRIVATE KEY-----
        MIIBOgIBAAJBALnfFW1FffeKPs5PLUhFOSkNrr9TDCODQAI3WluLh0sW7/ro93eo
        -----END RSA PRIVATE KEY-----
""")
    config.CONFIG.context = []

    with self.assertRaises(config_lib.ConfigFormatError):
      config.CONFIG.Get("PrivateKeys.executable_signing_private_key")

  def testRSAPublicKeySuccess(self):
    config.CONFIG.Initialize(data="""
[Client]
executable_signing_public_key = -----BEGIN PUBLIC KEY-----
    MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAzbuwYnKTTleU2F4zu1gI
    /BolzR74470j6wK7QrQp5b5QkmfevCdX540Ax3mFt6isChrhIXy4LmTvM5SeiCvs
    6su8ro7ZYqtbZjpoBWorESy5VAnnuiuwiAvI7IOPYbSu8e+mHQa893hLYv9q0kQe
    1CtlvQsKir8aQ0YC63UWhrcMcMYCjUaRkWo8JUWoCW/GuZjbuFF0ZZsA13cVSOhF
    g1dxvX4/+FXlnyZQbu2Aex4NU9NGYetl+SP10Uq/c92wZ34ENU3rH8Kw8Tar/dku
    g9+hgrcgt7JRECXmho+WFrKM1H6z1CNe6uEALMfogNl9Mm2jCgavl1wbV92pIKT1
    pQIDAQAB
    -----END PUBLIC KEY-----
""")
    config.CONFIG.context = []

    errors = config.CONFIG.Validate("Client")
    self.assertFalse(errors)

  def testRSAPublicKeyFailure(self):
    """Deliberately try to parse an invalid public key."""
    config.CONFIG.Initialize(data="""
[Client]
executable_signing_public_key = -----BEGIN PUBLIC KEY-----
        GpJgTFkTIAgX0Ih5lxoFB5TUjUfJFbBkSmKQPRA/IyuLBtCLQgwkTNkCAwEAAQ==
        -----END PUBLIC KEY-----
""")
    config.CONFIG.context = []

    errors = config.CONFIG.Validate("Client")
    self.assertCountEqual(
        list(errors.keys()), ["Client.executable_signing_public_key"]
    )

  def testRSAPrivate(self):
    """Tests parsing an RSA private key."""
    config.CONFIG.Initialize(data="""
[PrivateKeys]
executable_signing_private_key = -----BEGIN RSA PRIVATE KEY-----
    MIIEowIBAAKCAQEAzbuwYnKTTleU2F4zu1gI/BolzR74470j6wK7QrQp5b5Qkmfe
    vCdX540Ax3mFt6isChrhIXy4LmTvM5SeiCvs6su8ro7ZYqtbZjpoBWorESy5VAnn
    uiuwiAvI7IOPYbSu8e+mHQa893hLYv9q0kQe1CtlvQsKir8aQ0YC63UWhrcMcMYC
    jUaRkWo8JUWoCW/GuZjbuFF0ZZsA13cVSOhFg1dxvX4/+FXlnyZQbu2Aex4NU9NG
    Yetl+SP10Uq/c92wZ34ENU3rH8Kw8Tar/dkug9+hgrcgt7JRECXmho+WFrKM1H6z
    1CNe6uEALMfogNl9Mm2jCgavl1wbV92pIKT1pQIDAQABAoIBAAz6jaCm+T+HO2rg
    myizClK7JI4u6W/Wj1+Z+xh0wgg4wXT8VrBt1qK912Io0AR7gH+dB/2t6aGgTk3Q
    Tvr+CGgcj8E/CPGWUqxdkWaMDCj9IQ5El148N4VcTEyNanwfuFdSHBuMgLB89zEz
    i03grHA2nP24Jq4E6yIk1nYmW2mGoZSIrrSDG/VQj4NipeGxbwJsOGdFmzYlefk9
    lwC7Db9v2ocdytxlH7lxhVqEnOokLXT7VO/EPTyF3CcObZx2JG2P4d6KILcsRePg
    +xMTp0wmq4S3Hoiwi2+RZNH7aHn5igvcNbx0+Eu9CIKINuNwmw3c/2bAz6u48FUY
    8aUmQkECgYEA7cD3E8TqUTxQxCrcuHKVzbS5ThLvfSbIo7hctz2b9zshomRaeh1m
    qg3p5shQ0+p029H26mu8oi5e130QCmzbnhWoZZbVAY4SEe6+5SAF1d1Xhwn8jTZ5
    Vqo5B7ILKVvxHWkgdYFV9yi6c23/kSzFDZXW4QFt3eZgPv8wLxWU3uUCgYEA3YWh
    VcX2UDrQR8r4Qy9YHuQ85vW6O5QKvSz//Ckw9Z6TfFOf5DRmAHyt2IpnmmbeuhDD
    SsnXv1fsqJWcbl+/nP2cNuIhLXnUwebtTW3Qo9PSi7APhOYEYAbGuDiJ8swPof42
    5JjnIJ70dQv4wF1qHfu+ya+LPNnRZW2gF6Hbj8ECgYB+/Yu7Xnl9rIbDUNWWG3YS
    as5zej+7DEUs1aOIKHsvAcGEWK/O+/dDK61cnHA30MpcQ3jsW2FlCvmThfRUbTKc
    7JqGsJrTeswCEhCal5EmW1SOB3KDBq6m8MMHbjzx+W7/M5Cn0s5U9scoMn/ITi5u
    hDNC+Z1yYcPUwj89VvyuVQKBgCq9ztxC3vyp7Gf9xJsJ9oG3XfzeKrm2HcBUf2vC
    8txhZWmWpQIeDhRH+i8OvWCwOodCFrxGZ6dWqqX4f/9X4BvFXy/Dv80Ldb6X9O98
    ocYKZ9Rl+wiUbQGuLQd8eTlsoBOMfkDrM6U6pkYzMiLDo2b3nN9DTKVIDbv5Q+tr
    YnbBAoGBAMSqyBvyAsNdek5qvQ5yNqOl6X0HZJ/hp9HYz8gLyqmLWkQTjHUBI9zA
    KwJD5aLsPQCvKrE1oW66XkqI0p1KqZtkfL9ZfFH9A/AhpmEqtTStT62q/Ea21MDU
    AqJIPMXO96oTVY6eorI9BU0cG6n0UvzWZAxNT2UDK07UTB4v7Z8y
    -----END RSA PRIVATE KEY-----
""")
    config.CONFIG.context = []
    self.assertIsInstance(
        config.CONFIG.Get("PrivateKeys.executable_signing_private_key"),
        rdf_crypto.RSAPrivateKey,
    )


class CryptoUtilTest(CryptoTestBase):

  def testStreamingCBCEncryptor(self):
    key = rdf_crypto.EncryptionKey.GenerateKey()
    iv = rdf_crypto.EncryptionKey.GenerateKey()
    # 160 characters.
    message = b"Hello World!!!!!" * 10

    for plaintext, partitions in [
        (
            message,
            [
                [160],
                [80, 80],
                [75, 75, 10],
                [1, 159],
                [10] * 16,
                [1] * 160,
            ],
        ),
        # Prime length, not a multiple of blocksize.
        (
            message[:149],
            [
                [149],
                [80, 69],
                [75, 55, 19],
                [1, 148],
                [10] * 14 + [9],
                [1] * 149,
            ],
        ),
    ]:
      for partition in partitions:
        cipher = rdf_crypto.AES128CBCCipher(key, iv)
        streaming_cbc = rdf_crypto.StreamingCBCEncryptor(cipher)
        offset = 0
        out = []
        for n in partition:
          next_partition = plaintext[offset : offset + n]
          out.append(streaming_cbc.Update(next_partition))
          offset += n
        out.append(streaming_cbc.Finalize())

        self.assertEqual(cipher.Decrypt(b"".join(out)), plaintext)

  def testEncryptionKey(self):
    key = rdf_crypto.EncryptionKey.GenerateKey()
    iv = rdf_crypto.EncryptionKey.GenerateKey()

    self.assertNotEqual(key, iv)
    self.assertNotEqual(key.RawBytes(), iv.RawBytes())

    # This key is too short.
    self.assertRaises(rdf_crypto.CipherError, rdf_crypto.EncryptionKey, b"foo")

    copied_key = rdf_crypto.EncryptionKey(key.RawBytes())
    self.assertEqual(copied_key, key)
    self.assertEqual(copied_key.RawBytes(), key.RawBytes())

  def testAES128CBCCipher(self):
    key = rdf_crypto.EncryptionKey.GenerateKey()
    iv = rdf_crypto.EncryptionKey.GenerateKey()

    cipher = rdf_crypto.AES128CBCCipher(key, iv)

    plain_text = b"hello world!"
    cipher_text = cipher.Encrypt(plain_text)

    # Repeatedly calling Encrypt should repeat the same cipher text.
    self.assertEqual(cipher_text, cipher.Encrypt(plain_text))

    self.assertNotEqual(cipher_text, plain_text)
    self.assertEqual(cipher.Decrypt(cipher_text), plain_text)

    key2 = rdf_crypto.EncryptionKey.GenerateKey()
    iv2 = rdf_crypto.EncryptionKey.GenerateKey()
    cipher = rdf_crypto.AES128CBCCipher(key, iv2)
    self.assertRaises(rdf_crypto.CipherError, cipher.Decrypt, plain_text)
    cipher = rdf_crypto.AES128CBCCipher(key2, iv)
    self.assertRaises(rdf_crypto.CipherError, cipher.Decrypt, plain_text)
    cipher = rdf_crypto.AES128CBCCipher(key2, iv2)
    self.assertRaises(rdf_crypto.CipherError, cipher.Decrypt, plain_text)


class SymmetricCipherTest(
    rdf_test_base.RDFValueTestMixin, test_lib.GRRBaseTest
):
  rdfvalue_class = rdf_crypto.SymmetricCipher

  sample_cache = {}

  def GenerateSample(self, seed=1):
    # We need to generate consistent new samples for each seed.
    result = SymmetricCipherTest.sample_cache.get(seed)
    if result is None:
      result = self.rdfvalue_class.Generate("AES128CBC")
      SymmetricCipherTest.sample_cache[seed] = result

    return result

  def _testEncrypt(self, plain_text):
    sample = self.GenerateSample()
    self.assertLen(sample._key.RawBytes(), 16)
    self.assertLen(sample._iv.RawBytes(), 16)
    self.assertEqual(sample._key.RawBytes(), sample._key)

    cipher_text = sample.Encrypt(plain_text)
    self.assertNotEqual(cipher_text, plain_text)
    self.assertEqual(sample.Decrypt(cipher_text), plain_text)

  def testEncrypt(self):
    self._testEncrypt(b"hello world!")

  def testLargeEncrypt(self):
    # Test with a plaintext that is longer than blocksize.
    self._testEncrypt(b"hello world!" * 100)


class RSATest(CryptoTestBase):

  def testPassPhraseEncryption(self):
    passphrase = b"testtest"
    key = rdf_crypto.RSAPrivateKey.GenerateKey()
    protected_pem = key.AsPassphraseProtectedPEM(passphrase)
    unprotected_pem = key.AsPEM()

    with mock.patch.object(utils, "PassphraseCallback", lambda: passphrase):

      # Key from unprotected PEM should always work.
      rdf_crypto.RSAPrivateKey(unprotected_pem, allow_prompt=False)

      # Protected PEM does not work if we don't allow prompts.
      with self.assertRaises(type_info.TypeValueError):
        rdf_crypto.RSAPrivateKey(protected_pem, allow_prompt=False)

      # If we allow prompts, this will work.
      rdf_crypto.RSAPrivateKey(protected_pem, allow_prompt=True)

      # Default is to not ask unless we are in a command line context.
      with self.assertRaises(type_info.TypeValueError):
        rdf_crypto.RSAPrivateKey(protected_pem)

      with mock.patch.object(
          config.CONFIG,
          "context",
          config.CONFIG.context + ["Commandline Context"],
      ):
        rdf_crypto.RSAPrivateKey(protected_pem)

        # allow_prompt=False even prevents this in the Commandline Context.
        with self.assertRaises(type_info.TypeValueError):
          rdf_crypto.RSAPrivateKey(protected_pem, allow_prompt=False)

  def testSignVerify(self):

    private_key = rdf_crypto.RSAPrivateKey.GenerateKey(bits=2048)
    public_key = private_key.GetPublicKey()

    message = b"Hello World!"

    signature = private_key.Sign(message)

    # If this fails, it raises.
    public_key.Verify(message, signature)

    # Make sure it does.
    broken_signature = _Tamper(signature)
    broken_message = _Tamper(message)

    self.assertRaises(
        rdf_crypto.VerificationError,
        public_key.Verify,
        message,
        broken_signature,
    )
    self.assertRaises(
        rdf_crypto.VerificationError,
        public_key.Verify,
        broken_message,
        signature,
    )
    self.assertRaises(
        rdf_crypto.VerificationError, public_key.Verify, message, b""
    )

  def testEncryptDecrypt(self):
    private_key = rdf_crypto.RSAPrivateKey.GenerateKey(bits=2048)
    public_key = private_key.GetPublicKey()

    message = b"Hello World!"

    ciphertext = public_key.Encrypt(message)
    self.assertNotEqual(ciphertext, message)

    plaintext = private_key.Decrypt(ciphertext)
    self.assertEqual(plaintext, message)

    self.assertRaises(
        rdf_crypto.CipherError, private_key.Decrypt, _Tamper(ciphertext)
    )

  def testM2CryptoSigningCompatibility(self):
    pem = open(os.path.join(self.base_path, "m2crypto/rsa_key"), "rb").read()
    signature = open(
        os.path.join(self.base_path, "m2crypto/signature"), "rb"
    ).read()
    private_key = rdf_crypto.RSAPrivateKey(pem)
    message = b"Signed by M2Crypto!"

    public_key = private_key.GetPublicKey()

    # If this doesn't raise InvalidSignature, we are good.
    public_key.Verify(message, signature)

  def testM2CryptoEncryptionCompatibility(self):
    pem = open(os.path.join(self.base_path, "m2crypto/rsa_key"), "rb").read()
    private_key = rdf_crypto.RSAPrivateKey(pem)
    ciphertext = open(
        os.path.join(self.base_path, "m2crypto/rsa_ciphertext"), "rb"
    ).read()
    message = b"Encrypted by M2Crypto!"

    plaintext = private_key.Decrypt(ciphertext)
    self.assertEqual(plaintext, message)


class HMACTest(CryptoTestBase):

  def testHMAC(self):
    """A basic test for the HMAC class."""
    key = rdf_crypto.EncryptionKey.GenerateKey()
    message = b"Hello World!"
    h = rdf_crypto.HMAC(key)
    signature = h.HMAC(message)

    h.Verify(message, signature)

    broken_message = message + b"!"
    self.assertRaises(
        rdf_crypto.VerificationError, h.Verify, broken_message, signature
    )

    broken_signature = _Tamper(signature)
    self.assertRaises(
        rdf_crypto.VerificationError,
        h.Verify,
        b"Hello World!",
        broken_signature,
    )

  def testSHA256(self):
    """Tests that both types of signatures are ok."""
    key = rdf_crypto.EncryptionKey.GenerateKey()
    message = b"Hello World!"
    h = rdf_crypto.HMAC(key)
    signature_sha1 = h.HMAC(message)
    signature_sha256 = h.HMAC(message, use_sha256=True)

    self.assertNotEqual(signature_sha1, signature_sha256)
    h.Verify(message, signature_sha1)
    h.Verify(message, signature_sha256)

  def testM2CryptoCompatibility(self):
    message = b"HMAC by M2Crypto!"
    signature = binascii.unhexlify("99cae3ec7b41ceb6e6619f2f85368cb3ae118b70")
    key = rdf_crypto.EncryptionKey.FromHumanReadable(
        "94bd4e0ecc8397a8b2cdbc4b127ee7b0"
    )
    h = rdf_crypto.HMAC(key)

    self.assertEqual(h.HMAC(message), signature)

    h.Verify(message, signature)


class RDFX509CertTest(CryptoTestBase):

  def testExpiredTestCertificate(self):
    pem = open(
        os.path.join(self.base_path, "outdated_certificate"), "rb"
    ).read()
    certificate = rdf_crypto.RDFX509Cert(pem)

    exception_catcher = self.assertRaises(rdf_crypto.VerificationError)
    with exception_catcher:
      # We don't pass a proper key here, this will fail before it even touches
      # the key.
      certificate.Verify(None)

    self.assertIn("Certificate expired!", str(exception_catcher.exception))


class PasswordTest(CryptoTestBase):

  def testPassword(self):
    sample = jobs_pb2.Password()

    rdf_crypto.SetPassword(sample, "foo")
    serialized = sample.SerializeToString()
    self.assertNotIn(b"foo", serialized)

    read_sample = jobs_pb2.Password()
    read_sample.ParseFromString(serialized)

    self.assertFalse(rdf_crypto.CheckPassword(sample, "bar"))
    self.assertFalse(rdf_crypto.CheckPassword(read_sample, "bar"))
    self.assertTrue(rdf_crypto.CheckPassword(sample, "foo"))
    self.assertTrue(rdf_crypto.CheckPassword(read_sample, "foo"))


def _Tamper(string):
  return string[:-1] + bytes([string[-1] ^ 1])


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
