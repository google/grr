#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Client specific rdfvalue tests."""


import hashlib

from M2Crypto import RSA

from grr.lib import config_lib
from grr.lib import rdfvalue
from grr.lib.rdfvalues import test_base


class SignedBlobTest(test_base.RDFValueTestCase):
  rdfvalue_class = rdfvalue.SignedBlob

  def setUp(self):
    super(SignedBlobTest, self).setUp()
    self.private_key = config_lib.CONFIG[
        "PrivateKeys.driver_signing_private_key"]

    self.public_key = config_lib.CONFIG[
        "Client.driver_signing_public_key"]

  def GenerateSample(self, number=0):
    result = self.rdfvalue_class()
    result.Sign("Sample %s" % number, self.private_key)

    return result

  def testSignVerify(self):
    sample = self.GenerateSample()

    self.assertTrue(sample.Verify(self.public_key))

    # Change the data - this should fail since the hash is incorrect.
    sample.data += "X"
    self.assertRaises(rdfvalue.DecodeError, sample.Verify, self.public_key)

    # Update the hash
    sample.digest = hashlib.sha256(sample.data).digest()

    # Should still fail.
    self.assertRaises(rdfvalue.DecodeError, sample.Verify, self.public_key)

    # If we change the digest verification should fail.
    sample = self.GenerateSample()
    sample.digest_type = sample.HashType.MD5

    self.assertRaises(rdfvalue.DecodeError, sample.Verify, self.public_key)


class TestCryptoTypeInfos(test_base.RDFValueBaseTest):
  """Test that invalid configuration types are rejected.

  There is no need to check for success here because if that did not work we
  would not be able to run any tests.
  """

  def testX509Certificates(self):
    """Deliberately try to parse an invalid certificate."""
    config_lib.CONFIG.Initialize(data="""
[Frontend]
certificate = -----BEGIN CERTIFICATE-----
        MIIDczCCAVugAwIBAgIJANdK3LO+9qOIMA0GCSqGSIb3DQEBCwUAMFkxCzAJBgNV
        uqnFquJfg8xMWHHJmPEocDpJT8Tlmbw=
        -----END CERTIFICATE-----
""")

    errors = config_lib.CONFIG.Validate("Frontend")
    self.assertItemsEqual(errors.keys(), ["Frontend.certificate"])

  def testX509PrivateKey(self):
    """Deliberately try to parse an invalid server key."""
    config_lib.CONFIG.Initialize(data="""
[PrivateKeys]
server_key = -----BEGIN PRIVATE KEY-----
        MIICdwIBADANBgkqhkiG9w0BAQEFAASCAmEwggJdAgEAAoGBAMdgLNxyvDnQsuqp
        jzITFeE6mjs3k1I=
        -----END PRIVATE KEY-----
driver_signing_private_key = -----BEGIN RSA PRIVATE KEY-----
    MIIBOgIBAAJBALnfFW1FffeKPs5PLUhFOSkNrr9TDCODQAI3WluLh0sW7/ro93eo
    IZ0FbipnTpzGkPpriONbSOXmxWNTo0b9ma8CAwEAAQJAfg37HBZK7bxGB+jOjvrT
    XzI2Vu7dhqAWouojT357DMKjGvkO+w7r6BmToZkgHRL4Nvh1KJ/APYdWWR+jTwJ3
    4QIhAOhY/Gx8xs1ngrQLfSK9AWzPeegZK0I9W1UQuLWt7MjHAiEAzMrr2huBFrM0
    NgTOlWdrKnI/DPDpR3jGfSoUTsAeT9kCIQCzgxzzjKvkQtb+1+mEj1ashNgA9IEx
    mkoYPOUYqRnKPQIgUV+8UcEmDRgOAfzs/U7HtWkKBqFfgGfMLwXeZeBO6xkCIHGq
    wDcAa2GW9htKHmv9/Rzg05iAD+FYTsp8Gi2r4icV
    -----END RSA PRIVATE KEY-----
""")

    key = config_lib.CONFIG.Get("PrivateKeys.server_key")
    self.assertRaises(RSA.RSAError, key.GetPrivateKey)

  def testPEMPublicKey(self):
    """Deliberately try to parse an invalid public key."""
    config_lib.CONFIG.Initialize(data="""
[Client]
executable_signing_public_key = -----BEGIN PUBLIC KEY-----
        GpJgTFkTIAgX0Ih5lxoFB5TUjUfJFbBkSmKQPRA/IyuLBtCLQgwkTNkCAwEAAQ==
        -----END PUBLIC KEY-----

driver_signing_public_key = -----BEGIN PUBLIC KEY-----
    MFwwDQYJKoZIhvcNAQEBBQADSwAwSAJBALnfFW1FffeKPs5PLUhFOSkNrr9TDCOD
    QAI3WluLh0sW7/ro93eoIZ0FbipnTpzGkPpriONbSOXmxWNTo0b9ma8CAwEAAQ==
    -----END PUBLIC KEY-----
""")
    errors = config_lib.CONFIG.Validate("Client")
    self.assertItemsEqual(errors.keys(),
                          ["Client.executable_signing_public_key"])

  def testPEMPrivate(self):
    """Deliberately try to parse an invalid private key."""
    config_lib.CONFIG.Initialize(data="""
[PrivateKeys]
driver_signing_private_key = -----BEGIN RSA PRIVATE KEY-----
        MIIBOgIBAAJBALnfFW1FffeKPs5PLUhFOSkNrr9TDCODQAI3WluLh0sW7/ro93eo
        -----END RSA PRIVATE KEY-----
""")

    key = config_lib.CONFIG.Get("PrivateKeys.driver_signing_private_key")
    self.assertRaises(RSA.RSAError, key.GetPrivateKey)
