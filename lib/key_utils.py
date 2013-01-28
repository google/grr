#!/usr/bin/env python
# Copyright 2011 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""This file abstracts the loading of the private key."""


import random
import string
import time

from grr.client import conf as flags
from grr.lib import config_lib

from M2Crypto import ASN1
from M2Crypto import BIO
from M2Crypto import EVP
from M2Crypto import RSA
from M2Crypto import X509


FLAGS = flags.FLAGS
CONFIG = config_lib.CONFIG


# Modify the part below to implement any reasonable way of storing keys.
def GetCert(key_name):
  """Load a private key or cert from a PEM file.

  Args:
    key_name: Name of the key to load.

  Returns:
    String containing the key or cert.

  Raises:
    IOError: On failure to read key.
  """
  if not CONFIG.has_option("ServerKeys", key_name):
    raise IOError("Key %s not available in %s" % (key_name, FLAGS.config))
  data = CONFIG.get("ServerKeys", key_name)
  return data.strip()


def GenerateRSAKey(passphrase=None, key_length=2048):
  """Generate an RSA key and return tuple of pem strings for (priv,pub) keys."""
  if passphrase is not None:
    passphrase_cb = lambda: passphrase
  else:
    passphrase_cb = None
  key = RSA.gen_key(key_length, 65537)
  priv_key = key.as_pem(passphrase_cb)
  bio = BIO.MemoryBuffer()
  key.save_pub_key_bio(bio)
  pub_key = bio.read()
  return priv_key, pub_key


def MakeCSR(bits, common_name):
  """Create an X509 request.

  Args:
    bits: Number of RSA key bits.
    common_name: common name in the request

  Returns:
    An X509 request and the priv key.
  """
  pk = EVP.PKey()
  req = X509.Request()
  rsa = RSA.gen_key(bits, 65537, lambda: None)
  pk.assign_rsa(rsa)
  req.set_pubkey(pk)
  options = req.get_subject()
  options.C = "US"
  options.CN = common_name
  req.sign(pk, "sha256")
  return req, pk


def SetCertValidityDate(cert, days=365):
  """Set validity on a cert to specific number of days."""
  now_epoch = long(time.time())
  now = ASN1.ASN1_UTCTIME()
  now.set_time(now_epoch)
  expire = ASN1.ASN1_UTCTIME()
  expire.set_time(now_epoch + days * 24 * 60 * 60)
  cert.set_not_before(now)
  cert.set_not_after(expire)


def MakeCASignedCert(common_name, ca_pkey, bits=2048):
  """Make a cert and sign it with the CA. Return (cert, pkey)."""
  csr_req, pk = MakeCSR(bits, common_name=common_name)

  # Create our cert.
  cert = X509.X509()
  cert.set_serial_number(2)
  cert.set_version(2)
  SetCertValidityDate(cert)

  cert.set_subject(csr_req.get_subject())
  cert.set_pubkey(csr_req.get_pubkey())
  cert.sign(ca_pkey, "sha256")
  return cert, pk


def MakeCACert(common_name="grr", issuer_cn="grr_test", issuer_c="US"):
  """Generate a CA certificate.

  Args:
    common_name: Name for cert.
    issuer_cn: Name for issuer.
    issuer_c: Country for issuer.

  Returns:
    (Certificate, priv key, pub key).
  """
  req, pk = MakeCSR(2048, common_name=common_name)
  pkey = req.get_pubkey()
  cert = X509.X509()
  cert.set_serial_number(1)
  cert.set_version(2)
  SetCertValidityDate(cert, days=3650)

  issuer = X509.X509_Name()
  issuer.C = issuer_c
  issuer.CN = issuer_cn
  cert.set_issuer(issuer)

  cert.set_subject(cert.get_issuer())
  cert.set_pubkey(pkey)
  cert.add_ext(X509.new_extension("basicConstraints", "CA:TRUE"))
  cert.add_ext(X509.new_extension("subjectKeyIdentifier",
                                  cert.get_fingerprint()))
  cert.sign(pk, "sha256")
  return cert, pk, pkey


def GeneratePassphrase(length=20):
  """Create a 20 char passphrase with easily typeable chars."""
  valid_chars = string.ascii_letters + string.digits + " ,-_()&$#"
  return "".join(random.choice(valid_chars) for i in range(length))


