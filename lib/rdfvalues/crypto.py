#!/usr/bin/env python
"""Implementation of various cryprographic types."""


import hashlib
from M2Crypto import BIO
from M2Crypto import RSA
from M2Crypto import util
from M2Crypto import X509

import logging
from grr.lib import rdfvalue
from grr.lib import type_info
from grr.lib import utils
from grr.lib.rdfvalues import structs

from grr.proto import jobs_pb2

DIGEST_ALGORITHM = hashlib.sha256
DIGEST_ALGORITHM_STR = "sha256"


class Certificate(structs.RDFProtoStruct):
  protobuf = jobs_pb2.Certificate


class RDFX509Cert(rdfvalue.RDFString):
  """X509 certificates used to communicate with this client."""

  def _GetCN(self, x509cert):
    subject = x509cert.get_subject()
    try:
      cn_id = subject.nid["CN"]
      cn = subject.get_entries_by_nid(cn_id)[0]
    except IndexError:
      raise rdfvalue.DecodeError("Cert has no CN")

    self.common_name = rdfvalue.RDFURN(cn.get_data().as_text())

  def GetX509Cert(self):
    return X509.load_cert_string(str(self))

  def GetPubKey(self):
    return self.GetX509Cert().get_pubkey().get_rsa()

  def ParseFromString(self, string):
    super(RDFX509Cert, self).ParseFromString(string)
    try:
      self._GetCN(self.GetX509Cert())
    except X509.X509Error:
      raise rdfvalue.DecodeError("Cert invalid")


class SignedBlob(rdfvalue.RDFProtoStruct):
  """A signed blob.

  The client can receive and verify a signed blob (e.g. driver or executable
  binary). Once verified, the client may execute this.
  """
  protobuf = jobs_pb2.SignedBlob

  def Verify(self, pub_key):
    """Verify the data in this blob.

    Args:
      pub_key: The public key to use for verification.

    Returns:
      True when verification succeeds.

    Raises:
      rdfvalue.DecodeError if the data is not suitable verified.
    """
    if self.digest_type != self.HashType.SHA256:
      raise rdfvalue.DecodeError("Unsupported digest.")

    bio = BIO.MemoryBuffer(pub_key)
    rsa = RSA.load_pub_key_bio(bio)
    result = 0
    try:
      result = rsa.verify(self.digest, self.signature,
                          DIGEST_ALGORITHM_STR)
      if result != 1:
        raise rdfvalue.DecodeError("Could not verify blob.")

    except RSA.RSAError, e:
      raise rdfvalue.DecodeError("Could not verify blob. Error: %s" % e)

    digest = hashlib.sha256(self.data).digest()
    if digest != self.digest:
      raise rdfvalue.DecodeError(
          "SignedBlob: Digest did not match actual data.")

    if result != 1:
      raise rdfvalue.DecodeError("Verification failed.")

    return True

  def Sign(self, data, signing_key, verify_key=None, prompt=False):
    """Use the data to sign this blob.

    Args:
      data: String containing the blob data.
      signing_key: A key that can be loaded to sign the data as a string.
      verify_key: Key to verify with. If None we assume the signing key also
        contains the public key.
      prompt: If True we allow a password prompt to be presented.

    Raises:
      IOError: On bad key.
    """
    callback = None
    if prompt:
      callback = util.passphrase_callback
    else:
      callback = lambda x: ""

    digest = DIGEST_ALGORITHM(data).digest()
    rsa = RSA.load_key_string(signing_key, callback=callback)
    if len(rsa) < 2048:
      logging.warn("signing key is too short.")

    self.signature = rsa.sign(digest, DIGEST_ALGORITHM_STR)
    self.signature_type = self.SignatureType.RSA_2048

    self.digest = digest
    self.digest_type = self.HashType.SHA256
    self.data = data

    # Test we can verify before we send it off.
    if verify_key is None:
      m = BIO.MemoryBuffer()
      rsa.save_pub_key_bio(m)
      verify_key = m.read_all()

    # Verify our own data.
    self.Verify(verify_key)


class X509CertificateType(type_info.TypeInfoObject):
  """A type descriptor for an X509 certificate."""

  def Validate(self, value):
    """Ensure that value is a valid X509 certificate."""
    # An empty string is considered a valid certificate to allow us to load
    # config files with no certs filled in.
    if value:
      return self.ParseFromString(value)

    raise type_info.TypeValueError("No value set for %s" % self.name)

  def ParseFromString(self, cert_string):
    try:
      X509.load_cert_string(cert_string)
      return cert_string
    except X509.X509Error:
      raise type_info.TypeValueError("Certificate %s is invalid." % self.name)


class PEMPublicKey(X509CertificateType):
  """A Public key encoded as a pem file."""

  def ParseFromString(self, pem_string):
    try:
      bio = BIO.MemoryBuffer(pem_string)
      RSA.load_pub_key_bio(bio).check_key()
    except RSA.RSAError:
      raise type_info.TypeValueError("Public key %s is invalid." % self.name)


class PEMPrivateKey(X509CertificateType):
  """An RSA private key encoded as a pem file."""

  def ParseFromString(self, pem_string):
    try:
      rsa = RSA.load_key_string(pem_string, callback=lambda x: "")
      rsa.check_key()
    except RSA.RSAError:
      raise type_info.TypeValueError("Private key %s is invalid." % self.name)


class X509PrivateKey(X509CertificateType):
  """A type descriptor for a combined X509 certificate and private key."""

  def ParseFromString(self, cert_string):
    """Verify a certificate + private key pem config."""
    try:
      rsa = RSA.load_key_string(utils.SmartStr(cert_string),
                                callback=lambda x: "")
    except RSA.RSAError:
      raise type_info.TypeValueError("Private key %s is invalid." %
                                     self.name)

    # Now verify that rsa key is actually the private key that belongs to x509
    # key.
    if rsa.check_key() != 1:
      raise type_info.TypeValueError("Certificate and public key mismatch for "
                                     "%s." % self.name)
