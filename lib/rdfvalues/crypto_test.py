#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Client specific rdfvalue tests."""


import hashlib

from grr.lib import config_lib
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib import type_info
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
    sample.digest_type = 555

    self.assertRaises(rdfvalue.DecodeError, sample.Verify, self.public_key)


class TestCryptoTypeInfos(test_lib.GRRBaseTest):
  """Test that invalid configuration types are rejected.

  There is no need to check for success here because if that did not work we
  would not be able to run any tests.
  """

  def testX509Certificates(self):
    """Deliberately try to parse an invalid certificate."""
    self.assertRaises(type_info.TypeValueError, config_lib.CONFIG.Initialize,
                      data="""
[Frontend]
certificate = -----BEGIN CERTIFICATE-----
        MIIDczCCAVugAwIBAgIJANdK3LO+9qOIMA0GCSqGSIb3DQEBCwUAMFkxCzAJBgNV
        uqnFquJfg8xMWHHJmPEocDpJT8Tlmbw=
        -----END CERTIFICATE-----
""")

  def testX509PrivateKey(self):
    """Deliberately try to parse an invalid private key."""
    self.assertRaises(type_info.TypeValueError, config_lib.CONFIG.Initialize,
                      data="""
[PrivateKeys]
server_key = -----BEGIN PRIVATE KEY-----
        MIICdwIBADANBgkqhkiG9w0BAQEFAASCAmEwggJdAgEAAoGBAMdgLNxyvDnQsuqp
        jzITFeE6mjs3k1I=
        -----END PRIVATE KEY-----
""")

  def testPEMPublicKey(self):
    """Deliberately try to parse an invalid public key."""
    self.assertRaises(type_info.TypeValueError, config_lib.CONFIG.Initialize,
                      data="""
[Client]
executable_signing_public_key = -----BEGIN PUBLIC KEY-----
        GpJgTFkTIAgX0Ih5lxoFB5TUjUfJFbBkSmKQPRA/IyuLBtCLQgwkTNkCAwEAAQ==
        -----END PUBLIC KEY-----
""")

  def testPEMPrivate(self):
    """Deliberately try to parse an invalid public key."""
    self.assertRaises(type_info.TypeValueError, config_lib.CONFIG.Initialize,
                      data="""
[PrivateKeys]
driver_signing_private_key = -----BEGIN RSA PRIVATE KEY-----
        MIIBOgIBAAJBALnfFW1FffeKPs5PLUhFOSkNrr9TDCODQAI3WluLh0sW7/ro93eo
        -----END RSA PRIVATE KEY-----
""")
