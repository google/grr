#!/usr/bin/env python
"""This file abstracts the loading of the private key."""


import time

from M2Crypto import ASN1
from M2Crypto import BIO
from M2Crypto import EVP
from M2Crypto import RSA
from M2Crypto import X509


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


def MakeCACert(common_name="grr",
               issuer_cn="grr_test",
               issuer_c="US",
               bits=2048):
  """Generate a CA certificate.

  Args:
    common_name: Name for cert.
    issuer_cn: Name for issuer.
    issuer_c: Country for issuer.
    bits: Bit length of the key used.

  Returns:
    (Certificate, priv key, pub key).
  """
  req, pk = MakeCSR(bits, common_name=common_name)
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
  cert.add_ext(X509.new_extension("subjectKeyIdentifier", cert.get_fingerprint(
  )))
  cert.sign(pk, "sha256")
  return cert, pk, pkey
