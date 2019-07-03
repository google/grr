#!/usr/bin/env python
"""This file abstracts the loading of the private key."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from cryptography import x509
from cryptography.hazmat.backends import openssl
from cryptography.hazmat.primitives import hashes
from cryptography.x509 import oid

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import crypto as rdf_crypto


def MakeCASignedCert(common_name,
                     private_key,
                     ca_cert,
                     ca_private_key,
                     serial_number=2):
  """Make a cert and sign it with the CA's private key."""
  public_key = private_key.GetPublicKey()

  builder = x509.CertificateBuilder()

  builder = builder.issuer_name(ca_cert.GetIssuer())

  subject = x509.Name(
      [x509.NameAttribute(oid.NameOID.COMMON_NAME, common_name)])
  builder = builder.subject_name(subject)

  valid_from = rdfvalue.RDFDatetime.Now() - rdfvalue.Duration("1d")
  valid_until = rdfvalue.RDFDatetime.Now() + rdfvalue.Duration("3650d")
  builder = builder.not_valid_before(valid_from.AsDatetime())
  builder = builder.not_valid_after(valid_until.AsDatetime())

  builder = builder.serial_number(serial_number)
  builder = builder.public_key(public_key.GetRawPublicKey())

  builder = builder.add_extension(
      x509.BasicConstraints(ca=False, path_length=None), critical=True)
  certificate = builder.sign(
      private_key=ca_private_key.GetRawPrivateKey(),
      algorithm=hashes.SHA256(),
      backend=openssl.backend)
  return rdf_crypto.RDFX509Cert(certificate)


def MakeCACert(private_key,
               common_name=u"grr",
               issuer_cn=u"grr_test",
               issuer_c=u"US"):
  """Generate a CA certificate.

  Args:
    private_key: The private key to use.
    common_name: Name for cert.
    issuer_cn: Name for issuer.
    issuer_c: Country for issuer.

  Returns:
    The certificate.
  """
  public_key = private_key.GetPublicKey()

  builder = x509.CertificateBuilder()

  issuer = x509.Name([
      x509.NameAttribute(oid.NameOID.COMMON_NAME, issuer_cn),
      x509.NameAttribute(oid.NameOID.COUNTRY_NAME, issuer_c)
  ])
  subject = x509.Name(
      [x509.NameAttribute(oid.NameOID.COMMON_NAME, common_name)])
  builder = builder.subject_name(subject)
  builder = builder.issuer_name(issuer)

  valid_from = rdfvalue.RDFDatetime.Now() - rdfvalue.Duration("1d")
  valid_until = rdfvalue.RDFDatetime.Now() + rdfvalue.Duration("3650d")
  builder = builder.not_valid_before(valid_from.AsDatetime())
  builder = builder.not_valid_after(valid_until.AsDatetime())

  builder = builder.serial_number(1)
  builder = builder.public_key(public_key.GetRawPublicKey())

  builder = builder.add_extension(
      x509.BasicConstraints(ca=True, path_length=None), critical=True)
  builder = builder.add_extension(
      x509.SubjectKeyIdentifier.from_public_key(public_key.GetRawPublicKey()),
      critical=False)
  certificate = builder.sign(
      private_key=private_key.GetRawPrivateKey(),
      algorithm=hashes.SHA256(),
      backend=openssl.backend)
  return rdf_crypto.RDFX509Cert(certificate)
