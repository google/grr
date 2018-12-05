#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Crypto rdfvalue tests."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import hashlib
import os

from builtins import chr  # pylint: disable=redefined-builtin
from builtins import range  # pylint: disable=redefined-builtin
from future.utils import iterkeys

from grr_response_core import config
from grr_response_core.lib import config_lib
from grr_response_core.lib import flags
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import type_info
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import crypto as rdf_crypto
from grr_response_core.lib.rdfvalues import test_base as rdf_test_base
from grr.test_lib import test_lib


class SignedBlobTest(rdf_test_base.RDFValueTestMixin, test_lib.GRRBaseTest):
  rdfvalue_class = rdf_crypto.SignedBlob

  def setUp(self):
    super(SignedBlobTest, self).setUp()
    self.private_key = config.CONFIG[
        "PrivateKeys.executable_signing_private_key"]
    self.public_key = config.CONFIG["Client.executable_signing_public_key"]

  def GenerateSample(self, number=0):
    result = self.rdfvalue_class()
    result.Sign(b"Sample %s" % number, self.private_key)

    return result

  def testSignVerify(self):
    sample = self.GenerateSample()

    self.assertTrue(sample.Verify(self.public_key))

    # Change the data - this should fail since the hash is incorrect.
    sample.data += b"X"
    self.assertRaises(rdf_crypto.VerificationError, sample.Verify,
                      self.public_key)

    # Update the hash
    sample.digest = hashlib.sha256(sample.data).digest()

    # Should still fail.
    self.assertRaises(rdf_crypto.VerificationError, sample.Verify,
                      self.public_key)

    # If we change the digest verification should fail.
    sample = self.GenerateSample()
    sample.digest_type = sample.HashType.MD5

    self.assertRaises(rdfvalue.DecodeError, sample.Verify, self.public_key)

    # PSS should be accepted.
    sample = self.GenerateSample()
    sample.signature_type = sample.SignatureType.RSA_PSS
    sample.signature = self.private_key.Sign(sample.data, use_pss=1)
    sample.Verify(self.public_key)

  def testM2CryptoCompatibility(self):
    old_driver_signing_public_key = rdf_crypto.RSAPublicKey("""
-----BEGIN PUBLIC KEY-----
MFwwDQYJKoZIhvcNAQEBBQADSwAwSAJBALnfFW1FffeKPs5PLUhFOSkNrr9TDCOD
QAI3WluLh0sW7/ro93eoIZ0FbipnTpzGkPpriONbSOXmxWNTo0b9ma8CAwEAAQ==
-----END PUBLIC KEY-----
                                                        """)
    serialized_blob = open(
        os.path.join(self.base_path, "m2crypto/signed_blob"), "rb").read()
    blob = rdf_crypto.SignedBlob.FromSerializedString(serialized_blob)

    self.assertTrue(blob.Verify(old_driver_signing_public_key))


class CryptoTestBase(test_lib.GRRBaseTest):
  """Base class for all crypto tests here."""


class TestCryptoTypeInfos(CryptoTestBase):
  """Test that invalid configuration types are rejected.

  There is no need to check for success here because if that did not work we
  would not be able to run any tests.
  """

  def setUp(self):
    super(TestCryptoTypeInfos, self).setUp()
    self.config_stubber = test_lib.PreserveConfig()
    self.config_stubber.Start()

  def tearDown(self):
    super(TestCryptoTypeInfos, self).tearDown()
    self.config_stubber.Stop()

  def testInvalidX509Certificates(self):
    """Deliberately try to parse an invalid certificate."""
    config.CONFIG.Initialize(data="""
[Frontend]
certificate = -----BEGIN CERTIFICATE-----
        MIIDczCCAVugAwIBAgIJANdK3LO+9qOIMA0GCSqGSIb3DQEBCwUAMFkxCzAJBgNV
        uqnFquJfg8xMWHHJmPEocDpJT8Tlmbw=
        -----END CERTIFICATE-----
""")
    config.CONFIG.context = []

    errors = config.CONFIG.Validate("Frontend")
    self.assertCountEqual(list(iterkeys(errors)), ["Frontend.certificate"])

  def testInvalidRSAPrivateKey(self):
    """Deliberately try to parse invalid RSA keys."""
    config.CONFIG.Initialize(data="""
[PrivateKeys]
server_key = -----BEGIN PRIVATE KEY-----
        MIICdwIBADANBgkqhkiG9w0BAQEFAASCAmEwggJdAgEAAoGBAMdgLNxyvDnQsuqp
        jzITFeE6mjs3k1I=
        -----END PRIVATE KEY-----
executable_signing_private_key = -----BEGIN RSA PRIVATE KEY-----
        MIIBOgIBAAJBALnfFW1FffeKPs5PLUhFOSkNrr9TDCODQAI3WluLh0sW7/ro93eo
        -----END RSA PRIVATE KEY-----
""")
    config.CONFIG.context = []

    with self.assertRaises(config_lib.ConfigFormatError):
      config.CONFIG.Get("PrivateKeys.server_key")
    with self.assertRaises(config_lib.ConfigFormatError):
      config.CONFIG.Get("PrivateKeys.executable_signing_private_key")

  def testRSAPublicKeySuccess(self):
    config.CONFIG.Initialize(data="""
[Client]
executable_signing_public_key = -----BEGIN PUBLIC KEY-----
    MFwwDQYJKoZIhvcNAQEBBQADSwAwSAJBALnfFW1FffeKPs5PLUhFOSkNrr9TDCOD
    QAI3WluLh0sW7/ro93eoIZ0FbipnTpzGkPpriONbSOXmxWNTo0b9ma8CAwEAAQ==
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
        list(iterkeys(errors)), ["Client.executable_signing_public_key"])

  def testRSAPrivate(self):
    """Tests parsing an RSA private key."""
    config.CONFIG.Initialize(data="""
[PrivateKeys]
executable_signing_private_key = -----BEGIN RSA PRIVATE KEY-----
    MIIBOgIBAAJBALnfFW1FffeKPs5PLUhFOSkNrr9TDCODQAI3WluLh0sW7/ro93eo
    IZ0FbipnTpzGkPpriONbSOXmxWNTo0b9ma8CAwEAAQJAfg37HBZK7bxGB+jOjvrT
    XzI2Vu7dhqAWouojT357DMKjGvkO+w7r6BmToZkgHRL4Nvh1KJ/APYdWWR+jTwJ3
    4QIhAOhY/Gx8xs1ngrQLfSK9AWzPeegZK0I9W1UQuLWt7MjHAiEAzMrr2huBFrM0
    NgTOlWdrKnI/DPDpR3jGfSoUTsAeT9kCIQCzgxzzjKvkQtb+1+mEj1ashNgA9IEx
    mkoYPOUYqRnKPQIgUV+8UcEmDRgOAfzs/U7HtWkKBqFfgGfMLwXeZeBO6xkCIHGq
    wDcAa2GW9htKHmv9/Rzg05iAD+FYTsp8Gi2r4icV
    -----END RSA PRIVATE KEY-----
""")
    config.CONFIG.context = []
    self.assertIsInstance(
        config.CONFIG.Get("PrivateKeys.executable_signing_private_key"),
        rdf_crypto.RSAPrivateKey)


class CryptoUtilTest(CryptoTestBase):

  def testStreamingCBCEncryptor(self):
    key = rdf_crypto.AES128Key.GenerateKey()
    iv = rdf_crypto.AES128Key.GenerateKey()
    # 160 characters.
    message = b"Hello World!!!!!" * 10

    for plaintext, partitions in [
        (message, [
            [160],
            [80, 80],
            [75, 75, 10],
            [1, 159],
            [10] * 16,
            [1] * 160,
        ]),
        # Prime length, not a multiple of blocksize.
        (message[:149], [
            [149],
            [80, 69],
            [75, 55, 19],
            [1, 148],
            [10] * 14 + [9],
            [1] * 149,
        ])
    ]:
      for partition in partitions:
        cipher = rdf_crypto.AES128CBCCipher(key, iv)
        streaming_cbc = rdf_crypto.StreamingCBCEncryptor(cipher)
        it = iter(plaintext)
        out = []
        for n in partition:
          next_partition = b"".join([it.next() for _ in range(n)])
          out.append(streaming_cbc.Update(next_partition))
        out.append(streaming_cbc.Finalize())

        self.assertEqual(cipher.Decrypt(b"".join(out)), plaintext)

  def testAES128Key(self):
    key = rdf_crypto.AES128Key.GenerateKey()
    iv = rdf_crypto.AES128Key.GenerateKey()

    self.assertNotEqual(key, iv)
    self.assertNotEqual(key.RawBytes(), iv.RawBytes())

    # This key is too short.
    self.assertRaises(rdf_crypto.CipherError, rdf_crypto.AES128Key, b"foo")

    copied_key = rdf_crypto.AES128Key(key.RawBytes())
    self.assertEqual(copied_key, key)
    self.assertEqual(copied_key.RawBytes(), key.RawBytes())

  def testAES128CBCCipher(self):
    key = rdf_crypto.AES128Key.GenerateKey()
    iv = rdf_crypto.AES128Key.GenerateKey()

    cipher = rdf_crypto.AES128CBCCipher(key, iv)

    plain_text = b"hello world!"
    cipher_text = cipher.Encrypt(plain_text)

    # Repeatedly calling Encrypt should repeat the same cipher text.
    self.assertEqual(cipher_text, cipher.Encrypt(plain_text))

    self.assertNotEqual(cipher_text, plain_text)
    self.assertEqual(cipher.Decrypt(cipher_text), plain_text)

    key2 = rdf_crypto.AES128Key.GenerateKey()
    iv2 = rdf_crypto.AES128Key.GenerateKey()
    cipher = rdf_crypto.AES128CBCCipher(key, iv2)
    self.assertRaises(rdf_crypto.CipherError, cipher.Decrypt, plain_text)
    cipher = rdf_crypto.AES128CBCCipher(key2, iv)
    self.assertRaises(rdf_crypto.CipherError, cipher.Decrypt, plain_text)
    cipher = rdf_crypto.AES128CBCCipher(key2, iv2)
    self.assertRaises(rdf_crypto.CipherError, cipher.Decrypt, plain_text)


class SymmetricCipherTest(rdf_test_base.RDFValueTestMixin,
                          test_lib.GRRBaseTest):
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

  def _Tamper(self, string):
    return string[:-1] + chr(ord(string[-1]) ^ 1).encode("latin-1")

  def testPassPhraseEncryption(self):
    passphrase = b"testtest"
    key = rdf_crypto.RSAPrivateKey.GenerateKey()
    protected_pem = key.AsPassphraseProtectedPEM(passphrase)
    unprotected_pem = key.AsPEM()

    with utils.Stubber(utils, "PassphraseCallback", lambda: passphrase):

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

      with utils.Stubber(config.CONFIG, "context",
                         config.CONFIG.context + ["Commandline Context"]):
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
    broken_signature = self._Tamper(signature)
    broken_message = self._Tamper(message)

    self.assertRaises(rdf_crypto.VerificationError, public_key.Verify, message,
                      broken_signature)
    self.assertRaises(rdf_crypto.VerificationError, public_key.Verify,
                      broken_message, signature)
    self.assertRaises(rdf_crypto.VerificationError, public_key.Verify, message,
                      b"")

  def testEncryptDecrypt(self):
    private_key = rdf_crypto.RSAPrivateKey.GenerateKey(bits=2048)
    public_key = private_key.GetPublicKey()

    message = b"Hello World!"

    ciphertext = public_key.Encrypt(message)
    self.assertNotEqual(ciphertext, message)

    plaintext = private_key.Decrypt(ciphertext)
    self.assertEqual(plaintext, message)

    self.assertRaises(rdf_crypto.CipherError, private_key.Decrypt,
                      self._Tamper(ciphertext))

  def testPSSPadding(self):
    private_key = rdf_crypto.RSAPrivateKey.GenerateKey(bits=2048)
    public_key = private_key.GetPublicKey()
    message = b"Hello World!"

    # Generate two different signtures, one using PKCS1v15 padding, one using
    # PSS. The crypto code should accept both as valid.
    signature_pkcs1v15 = private_key.Sign(message)
    signature_pss = private_key.Sign(message, use_pss=True)
    self.assertNotEqual(signature_pkcs1v15, signature_pss)
    public_key.Verify(message, signature_pkcs1v15)
    public_key.Verify(message, signature_pss)

  def testM2CryptoSigningCompatibility(self):
    pem = open(os.path.join(self.base_path, "m2crypto/rsa_key"), "rb").read()
    signature = open(os.path.join(self.base_path, "m2crypto/signature"),
                     "rb").read()
    private_key = rdf_crypto.RSAPrivateKey(pem)
    message = b"Signed by M2Crypto!"

    public_key = private_key.GetPublicKey()

    # If this doesn't raise InvalidSignature, we are good.
    public_key.Verify(message, signature)

  def testM2CryptoEncryptionCompatibility(self):
    pem = open(os.path.join(self.base_path, "m2crypto/rsa_key"), "rb").read()
    private_key = rdf_crypto.RSAPrivateKey(pem)
    ciphertext = open(
        os.path.join(self.base_path, "m2crypto/rsa_ciphertext"), "rb").read()
    message = b"Encrypted by M2Crypto!"

    plaintext = private_key.Decrypt(ciphertext)
    self.assertEqual(plaintext, message)


class HMACTest(CryptoTestBase):

  def _Tamper(self, string):
    return string[:-1] + chr(ord(string[-1]) ^ 1).encode("latin-1")

  def testHMAC(self):
    """A basic test for the HMAC class."""
    key = rdf_crypto.EncryptionKey.GenerateKey()
    message = b"Hello World!"
    h = rdf_crypto.HMAC(key)
    signature = h.HMAC(message)

    h.Verify(message, signature)

    broken_message = message + b"!"
    self.assertRaises(rdf_crypto.VerificationError, h.Verify, broken_message,
                      signature)

    broken_signature = self._Tamper(signature)
    self.assertRaises(rdf_crypto.VerificationError, h.Verify, b"Hello World!",
                      broken_signature)

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
    signature = "99cae3ec7b41ceb6e6619f2f85368cb3ae118b70".decode("hex")
    key = rdf_crypto.EncryptionKey.FromHex("94bd4e0ecc8397a8b2cdbc4b127ee7b0")
    h = rdf_crypto.HMAC(key)

    self.assertEqual(h.HMAC(message), signature)

    h.Verify(message, signature)


class RDFX509CertTest(CryptoTestBase):

  def testCertificateVerification(self):
    private_key = rdf_crypto.RSAPrivateKey.GenerateKey()
    csr = rdf_crypto.CertificateSigningRequest(
        common_name="C.0000000000000001", private_key=private_key)
    client_cert = rdf_crypto.RDFX509Cert.ClientCertFromCSR(csr)

    ca_signing_key = config.CONFIG["PrivateKeys.ca_key"]

    csr.Verify(private_key.GetPublicKey())
    client_cert.Verify(ca_signing_key.GetPublicKey())

    wrong_key = rdf_crypto.RSAPrivateKey.GenerateKey()
    with self.assertRaises(rdf_crypto.VerificationError):
      csr.Verify(wrong_key.GetPublicKey())

    with self.assertRaises(rdf_crypto.VerificationError):
      client_cert.Verify(wrong_key.GetPublicKey())

  def testExpiredTestCertificate(self):
    pem = open(os.path.join(self.base_path, "outdated_certificate"),
               "rb").read()
    certificate = rdf_crypto.RDFX509Cert(pem)

    exception_catcher = self.assertRaises(rdf_crypto.VerificationError)
    with exception_catcher:
      # We don't pass a proper key here, this will fail before it even touches
      # the key.
      certificate.Verify(None)

    self.assertIn("Certificate expired!", str(exception_catcher.exception))

  def testCertificateValidation(self):
    private_key = rdf_crypto.RSAPrivateKey.GenerateKey()
    csr = rdf_crypto.CertificateSigningRequest(
        common_name="C.0000000000000001", private_key=private_key)
    client_cert = rdf_crypto.RDFX509Cert.ClientCertFromCSR(csr)

    now = rdfvalue.RDFDatetime.Now()
    now_plus_year_and_a_bit = now + rdfvalue.Duration("55w")
    now_minus_a_bit = now - rdfvalue.Duration("1h")
    with test_lib.FakeTime(now_plus_year_and_a_bit):
      with self.assertRaises(rdf_crypto.VerificationError):
        client_cert.Verify(private_key.GetPublicKey())

    with test_lib.FakeTime(now_minus_a_bit):
      with self.assertRaises(rdf_crypto.VerificationError):
        client_cert.Verify(private_key.GetPublicKey())


class PasswordTest(CryptoTestBase):

  def testPassword(self):
    sample = rdf_crypto.Password()

    sample.SetPassword(b"foo")
    serialized = sample.SerializeToString()
    self.assertNotIn(b"foo", serialized)

    read_sample = rdf_crypto.Password.FromSerializedString(serialized)

    self.assertFalse(sample.CheckPassword(b"bar"))
    self.assertFalse(read_sample.CheckPassword(b"bar"))
    self.assertTrue(sample.CheckPassword(b"foo"))
    self.assertTrue(read_sample.CheckPassword(b"foo"))


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
