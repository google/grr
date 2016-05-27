#!/usr/bin/env python
"""Implementation of various cryptographic types."""


import hashlib
import struct


from M2Crypto import BIO
from M2Crypto import EVP
from M2Crypto import RSA
from M2Crypto import util
from M2Crypto import X509

import logging
from grr.lib import rdfvalue
from grr.lib import type_info
from grr.lib import utils
from grr.lib.rdfvalues import structs as rdf_structs

from grr.proto import jobs_pb2

DIGEST_ALGORITHM = hashlib.sha256
DIGEST_ALGORITHM_STR = "sha256"


class CipherError(rdfvalue.DecodeError):
  """Raised when decryption failed."""


class Certificate(rdf_structs.RDFProtoStruct):
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


class PEMPublicKey(rdfvalue.RDFString):
  """A Public key encoded as a pem file."""

  def GetPublicKey(self):
    try:
      bio = BIO.MemoryBuffer(self._value)
      rsa = RSA.load_pub_key_bio(bio)
      if rsa.check_key() != 1:
        raise CipherError("RSA.check_key() did not succeed.")

      return rsa
    except RSA.RSAError as e:
      raise type_info.TypeValueError("Public key invalid: %s" % e)

  def ParseFromString(self, pem_string):
    super(PEMPublicKey, self).ParseFromString(pem_string)
    self.GetPublicKey()


class PEMPrivateKey(rdfvalue.RDFString):
  """An RSA private key encoded as a pem file."""

  _private_key_cache = None

  def GetPrivateKey(self, callback=None):
    if callback is None:
      callback = lambda: ""

    # Cache the decoded private key so it does not need to be unlocked all the
    # time. Unfortunately due to M2Crypto's horrible memory management issues we
    # can only ever hold a reference to strings so we need to PEM encode the
    # private key with no password and cache that.
    if self._private_key_cache:
      return RSA.load_key_string(self._private_key_cache)

    # Unlock the private key if needed.
    private_key = RSA.load_key_string(self._value, callback=callback)

    # Re-encode it as a PEM and cache that.
    m = BIO.MemoryBuffer()
    private_key.save_key_bio(m, cipher=None)
    self._private_key_cache = m.getvalue()

    return private_key

  def GetPublicKey(self):
    rsa = self.GetPrivateKey()
    m = BIO.MemoryBuffer()
    rsa.save_pub_key_bio(m)
    return PEMPublicKey(m.read_all())

  def Validate(self):
    try:
      rsa = self.GetPrivateKey()
      rsa.check_key()
    except RSA.RSAError as e:
      raise type_info.TypeValueError("Private key invalid: %s" % e)

  @classmethod
  def GenKey(cls, bits=2048, exponent=65537):
    return cls(RSA.gen_key(bits, exponent).as_pem(None))


class Hash(rdf_structs.RDFProtoStruct):
  """A hash object containing multiple digests."""
  protobuf = jobs_pb2.Hash


class SignedBlob(rdf_structs.RDFProtoStruct):
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

    rsa = pub_key.GetPublicKey()
    result = 0
    try:
      result = rsa.verify(self.digest, self.signature, DIGEST_ALGORITHM_STR)
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

    Returns:
      self for call chaining.

    Raises:
      IOError: On bad key.
    """
    callback = None
    if prompt:
      callback = util.passphrase_callback
    else:
      callback = lambda x: ""

    digest = DIGEST_ALGORITHM(data).digest()
    rsa = signing_key.GetPrivateKey(callback=callback)
    if len(rsa) < 2048:
      logging.warn("signing key is too short.")

    self.signature = rsa.sign(digest, DIGEST_ALGORITHM_STR)
    self.signature_type = self.SignatureType.RSA_2048

    self.digest = digest
    self.digest_type = self.HashType.SHA256
    self.data = data

    # Test we can verify before we send it off.
    if verify_key is None:
      verify_key = signing_key.GetPublicKey()

    # Verify our own data.
    self.Verify(verify_key)

    return self


class EncryptionKey(rdfvalue.RDFBytes):
  """Base class for encryption keys."""
  # Size of the key in bits.
  length = 128

  def __init__(self, *args, **kwargs):
    super(EncryptionKey, self).__init__(*args, **kwargs)
    if not self._value:
      self.Generate()

  def ParseFromString(self, string):
    # Support both hex encoded and raw serializations.
    if len(string) == 2 * self.length / 8:
      self._value = string.decode("hex")
    elif len(string) == self.length / 8:
      self._value = string

    else:
      raise CipherError("%s must be exactly %s bits long." %
                        (self.__class__.__name__, self.length))

  def __str__(self):
    return self._value.encode("hex")

  def Generate(self):
    self._value = ""
    while len(self._value) < self.length / 8:
      self._value += struct.pack("=L", utils.PRNG.GetULong())

    self._value = self._value[:self.length / 8]
    return self

  def RawBytes(self):
    return self._value


class AES128Key(EncryptionKey):
  length = 128


class AutoGeneratedAES128Key(AES128Key):
  """Like AES128Key, but its UI edit box is prefilled with generated key."""

  def __init__(self, initializer=None, **kwargs):
    if isinstance(initializer, AES128Key):
      super(AutoGeneratedAES128Key, self).__init__(
          initializer=initializer.RawBytes(),
          **kwargs)
    else:
      super(AutoGeneratedAES128Key, self).__init__(initializer=initializer,
                                                   **kwargs)


class Cipher(object):
  """A Cipher that accepts rdfvalue.EncryptionKey objects as key and iv."""

  OP_DECRYPT = 0
  OP_ENCRYPT = 1

  algorithm = None

  def __init__(self, key, iv, mode=None):
    self.key = key.RawBytes()
    self.iv = iv.RawBytes()
    if mode is None:
      mode = self.OP_DECRYPT

    self.mode = mode
    self.Reinitialize()

  def Reinitialize(self):
    self.cipher = EVP.Cipher(alg=self.algorithm,
                             key=self.key,
                             iv=self.iv,
                             op=self.mode)

  def Update(self, data):
    """Encrypts the data up to blocksize."""
    try:
      return self.cipher.update(data)
    except EVP.EVPError as e:
      raise CipherError(e)

  def Final(self):
    """Pad the message to blocksize and finalize it."""
    try:
      return self.cipher.final()
    except EVP.EVPError as e:
      raise CipherError(e)

  def Encrypt(self, data):
    """A convenience method which pads and encrypts at once."""
    self.mode = self.OP_ENCRYPT
    self.Reinitialize()

    try:
      return self.Update(data) + self.Final()
    except EVP.EVPError as e:
      raise CipherError(e)

  def Decrypt(self, data):
    """A convenience method which pads and encrypts at once."""
    self.mode = self.OP_DECRYPT
    self.Reinitialize()

    try:
      return self.Update(data) + self.Final()
    except EVP.EVPError as e:
      raise CipherError(e)


class AES128CBCCipher(Cipher):
  """An aes_128_cbc cipher."""

  algorithm = "aes_128_cbc"


class SymmetricCipher(rdf_structs.RDFProtoStruct):
  """Abstract symmetric cipher operations."""
  protobuf = jobs_pb2.SymmetricCipher

  cipher = None

  def SetAlgorithm(self, algorithm):
    self._algorithm = algorithm
    if algorithm == self.Algorithm.AES128CBC:
      self.key = AES128Key()
      self._key = self.key.RawBytes()
      self.iv = AES128Key()
      self._iv = self.iv.RawBytes()
      return self

    else:
      raise RuntimeError("Algorithm not supported.")

  def _get_cipher(self):
    if self._algorithm == self.Algorithm.AES128CBC:
      return AES128CBCCipher(AES128Key(self._key), AES128Key(self._iv))

    raise CipherError("Unknown cipher type %s" % self._algorithm)

  def Encrypt(self, data):
    if self._algorithm == self.Algorithm.NONE:
      raise TypeError("Empty encryption is not allowed.")

    return self._get_cipher().Encrypt(data)

  def Decrypt(self, data):
    if self._algorithm == self.Algorithm.NONE:
      raise TypeError("Empty encryption is not allowed.")

    return self._get_cipher().Decrypt(data)
