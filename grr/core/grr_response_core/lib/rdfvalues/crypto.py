#!/usr/bin/env python
"""Implementation of various cryptographic types."""

import binascii
import hashlib
import logging
import os
from typing import Text

from cryptography import exceptions
from cryptography import x509
from cryptography.hazmat.backends import openssl
from cryptography.hazmat.primitives import ciphers
from cryptography.hazmat.primitives import constant_time
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import hmac
from cryptography.hazmat.primitives import padding as sym_padding
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.ciphers import algorithms
from cryptography.hazmat.primitives.ciphers import modes
from cryptography.hazmat.primitives.kdf import pbkdf2
from cryptography.x509 import oid

from grr_response_core.lib import config_lib
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import type_info
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import standard as rdf_standard
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.lib.util import precondition
from grr_response_core.lib.util import random
from grr_response_core.lib.util import text
from grr_response_proto import jobs_pb2


class Error(Exception):
  pass


class VerificationError(Error):
  pass


class InvalidSignature(Error):
  pass


class CipherError(rdfvalue.DecodeError):
  """Raised when decryption failed."""


class Certificate(rdf_structs.RDFProtoStruct):
  protobuf = jobs_pb2.Certificate


class RDFX509Cert(rdfvalue.RDFPrimitive):
  """X509 certificates used to communicate with this client."""

  def __init__(self, initializer=None):
    if initializer is None:
      super().__init__(None)
    elif isinstance(initializer, RDFX509Cert):
      super().__init__(initializer._value)  # pylint: disable=protected-access
    elif isinstance(initializer, x509.Certificate):
      super().__init__(initializer)
    elif isinstance(initializer, bytes):
      try:
        value = x509.load_pem_x509_certificate(
            initializer, backend=openssl.backend)
      except (ValueError, TypeError) as e:
        raise rdfvalue.DecodeError("Invalid certificate %s: %s" %
                                   (initializer, e))
      super().__init__(value)
    else:
      raise rdfvalue.InitializeError("Cannot initialize %s from %s." %
                                     (self.__class__, initializer))
    if self._value is not None:
      self.GetCN()  # This can also raise if there isn't exactly one CN entry.

  def GetRawCertificate(self):
    return self._value

  def GetCN(self):
    subject = self._value.subject
    try:
      cn_attributes = subject.get_attributes_for_oid(oid.NameOID.COMMON_NAME)
      if len(cn_attributes) > 1:
        raise rdfvalue.DecodeError("Cert has more than 1 CN entries.")
      cn_attribute = cn_attributes[0]
    except IndexError:
      raise rdfvalue.DecodeError("Cert has no CN")

    return cn_attribute.value

  def GetPublicKey(self):
    return RSAPublicKey(self._value.public_key())

  def GetSerialNumber(self):
    return self._value.serial_number

  def GetIssuer(self):
    return self._value.issuer

  @classmethod
  def FromSerializedBytes(cls, value: bytes):
    precondition.AssertType(value, bytes)
    return cls(value)

  @classmethod
  def FromHumanReadable(cls, string: Text):
    precondition.AssertType(string, Text)
    return cls.FromSerializedBytes(string.encode("ascii"))

  @classmethod
  def FromWireFormat(cls, value):
    precondition.AssertType(value, bytes)
    return cls.FromSerializedBytes(value)

  def SerializeToBytes(self) -> bytes:
    if self._value is None:
      return b""
    return self._value.public_bytes(encoding=serialization.Encoding.PEM)

  # TODO(user): this should return a string, since PEM format
  # base64-encodes data and thus is ascii-compatible.
  def AsPEM(self):
    return self.SerializeToBytes()

  def __str__(self) -> Text:
    return self.SerializeToBytes().decode("ascii")

  def Verify(self, public_key):
    """Verifies the certificate using the given key.

    Args:
      public_key: The public key to use.

    Returns:
      True: Everything went well.

    Raises:
      VerificationError: The certificate did not verify.
    """
    # TODO(amoser): We have to do this manually for now since cryptography does
    # not yet support cert verification. There is PR 2460:
    # https://github.com/pyca/cryptography/pull/2460/files
    # that will add it, once it's in we should switch to using this.

    # Note that all times here are in UTC.
    now = rdfvalue.RDFDatetime.Now().AsDatetime()
    if now > self._value.not_valid_after:
      raise VerificationError("Certificate expired!")
    if now < self._value.not_valid_before:
      raise VerificationError("Certificate not yet valid!")

    public_key.Verify(
        self._value.tbs_certificate_bytes,
        self._value.signature,
        hash_algorithm=self._value.signature_hash_algorithm)
    return True

  @classmethod
  def ClientCertFromCSR(cls, csr):
    """Creates a new cert for the given common name.

    Args:
      csr: A CertificateSigningRequest.

    Returns:
      The signed cert.
    """
    builder = x509.CertificateBuilder()
    # Use the client CN for a cert serial_id. This will ensure we do
    # not have clashing cert id.
    common_name = csr.GetCN()
    serial = int(common_name.split(".")[1], 16)
    builder = builder.serial_number(serial)
    builder = builder.subject_name(
        x509.Name(
            [x509.NameAttribute(oid.NameOID.COMMON_NAME, str(common_name))]))

    now = rdfvalue.RDFDatetime.Now()
    now_plus_year = now + rdfvalue.Duration.From(52, rdfvalue.WEEKS)
    builder = builder.not_valid_after(now_plus_year.AsDatetime())
    now_minus_ten = now - rdfvalue.Duration.From(10, rdfvalue.SECONDS)
    builder = builder.not_valid_before(now_minus_ten.AsDatetime())
    # TODO(user): dependency loop with
    # grr/core/grr_response_core/config/client.py.
    # pylint: disable=protected-access
    ca_cert = config_lib._CONFIG["CA.certificate"]
    # pylint: enable=protected-access
    builder = builder.issuer_name(ca_cert.GetIssuer())
    builder = builder.public_key(csr.GetPublicKey().GetRawPublicKey())

    # TODO(user): dependency loop with
    # grr/core/grr_response_core/config/client.py.
    # pylint: disable=protected-access
    ca_key = config_lib._CONFIG["PrivateKeys.ca_key"]
    # pylint: enable=protected-access

    return RDFX509Cert(
        builder.sign(
            private_key=ca_key.GetRawPrivateKey(),
            algorithm=hashes.SHA256(),
            backend=openssl.backend))


class CertificateSigningRequest(rdfvalue.RDFPrimitive):
  """A CSR Rdfvalue."""

  def __init__(self, initializer=None, common_name=None, private_key=None):
    if isinstance(initializer, CertificateSigningRequest):
      super().__init__(initializer._value)  # pylint: disable=protected-access
    if isinstance(initializer, x509.CertificateSigningRequest):
      super().__init__(initializer)
    elif isinstance(initializer, bytes):
      value = x509.load_pem_x509_csr(initializer, backend=openssl.backend)
      super().__init__(value)
    elif common_name and private_key:
      value = x509.CertificateSigningRequestBuilder().subject_name(
          x509.Name(
              [x509.NameAttribute(oid.NameOID.COMMON_NAME,
                                  str(common_name))])).sign(
                                      private_key.GetRawPrivateKey(),
                                      hashes.SHA256(),
                                      backend=openssl.backend)
      super().__init__(value)
    elif initializer is not None:
      raise rdfvalue.InitializeError("Cannot initialize %s from %s." %
                                     (self.__class__, initializer))

  @classmethod
  def FromSerializedBytes(cls, value: bytes):
    precondition.AssertType(value, bytes)
    return cls(value)

  @classmethod
  def FromWireFormat(cls, value):
    precondition.AssertType(value, bytes)
    return cls.FromSerializedBytes(value)

  def SerializeToBytes(self) -> bytes:
    if self._value is None:
      return b""
    return self._value.public_bytes(serialization.Encoding.PEM)

  # TODO(user): this should return a string, since PEM format
  # base64-encodes data and thus is ascii-compatible.
  def AsPEM(self):
    return self.SerializeToBytes()

  def __str__(self) -> Text:
    return self.SerializeToBytes().decode("ascii")

  def GetCN(self):
    subject = self._value.subject
    try:
      cn_attributes = subject.get_attributes_for_oid(oid.NameOID.COMMON_NAME)
      if len(cn_attributes) > 1:
        raise rdfvalue.DecodeError("CSR has more than 1 CN entries.")
      cn_attribute = cn_attributes[0]
    except IndexError:
      raise rdfvalue.DecodeError("CSR has no CN")

    return cn_attribute.value

  def GetPublicKey(self):
    return RSAPublicKey(self._value.public_key())

  def Verify(self, public_key):
    public_key.Verify(
        self._value.tbs_certrequest_bytes,
        self._value.signature,
        hash_algorithm=self._value.signature_hash_algorithm)
    return True


class RSAPublicKey(rdfvalue.RDFPrimitive):
  """An RSA public key."""

  def __init__(self, initializer=None):
    if isinstance(initializer, RSAPublicKey):
      initializer = initializer._value  # pylint: disable=protected-access

    if initializer is None:
      super().__init__(None)
      return

    if isinstance(initializer, rsa.RSAPublicKey):
      super().__init__(initializer)
      return

    if isinstance(initializer, Text):
      initializer = initializer.encode("ascii")

    if isinstance(initializer, bytes):
      try:
        value = serialization.load_pem_public_key(
            initializer, backend=openssl.backend)
        super().__init__(value)
        return
      except (TypeError, ValueError, exceptions.UnsupportedAlgorithm) as e:
        raise type_info.TypeValueError("Public key invalid: %s" % e)

    raise rdfvalue.InitializeError("Cannot initialize %s from %s." %
                                   (self.__class__, initializer))

  def GetRawPublicKey(self):
    return self._value

  @classmethod
  def FromSerializedBytes(cls, value: bytes):
    precondition.AssertType(value, bytes)
    return cls(value)

  @classmethod
  def FromWireFormat(cls, value):
    precondition.AssertType(value, bytes)
    return cls.FromSerializedBytes(value)

  @classmethod
  def FromHumanReadable(cls, string: Text):
    precondition.AssertType(string, Text)
    return cls.FromSerializedBytes(string.encode("ascii"))

  def SerializeToBytes(self) -> bytes:
    if self._value is None:
      return b""
    return self._value.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo)

  def GetN(self):
    return self._value.public_numbers().n

  def __str__(self) -> Text:
    return self.SerializeToBytes().decode("ascii")

  # TODO(user): this should return a string, since PEM format
  # base64-encodes data and thus is ascii-compatible.
  def AsPEM(self):
    return self.SerializeToBytes()

  def KeyLen(self):
    if self._value is None:
      return 0
    return self._value.key_size

  def Encrypt(self, message):
    if self._value is None:
      raise ValueError("Can't Encrypt with empty key.")

    try:
      return self._value.encrypt(
          message,
          padding.OAEP(
              mgf=padding.MGF1(algorithm=hashes.SHA1()),
              algorithm=hashes.SHA1(),
              label=None))
    except ValueError as e:
      raise CipherError(e)

  def Verify(self, message, signature, hash_algorithm=None):
    """Verifies a given message."""
    # This method accepts both PSS and PKCS1v15 padding. PSS is preferred but
    # old clients only support PKCS1v15.

    if hash_algorithm is None:
      hash_algorithm = hashes.SHA256()

    last_e = None
    for padding_algorithm in [
        padding.PSS(
            mgf=padding.MGF1(hash_algorithm),
            salt_length=padding.PSS.MAX_LENGTH),
        padding.PKCS1v15()
    ]:
      try:
        self._value.verify(signature, message, padding_algorithm,
                           hash_algorithm)
        return True

      except exceptions.InvalidSignature as e:
        last_e = e

    raise VerificationError(last_e)


class RSAPrivateKey(rdfvalue.RDFPrimitive):
  """An RSA private key."""

  def __init__(self, initializer=None, allow_prompt=None):

    if isinstance(initializer, RSAPrivateKey):
      initializer = initializer._value  # pylint: disable=protected-access

    if initializer is None:
      super().__init__(None)
      return

    if isinstance(initializer, rsa.RSAPrivateKey):
      super().__init__(initializer)
      return

    if isinstance(initializer, Text):
      initializer = initializer.encode("ascii")

    if not isinstance(initializer, bytes):
      raise rdfvalue.InitializeError("Cannot initialize %s from %s." %
                                     (self.__class__, initializer))

    try:
      value = serialization.load_pem_private_key(
          initializer, password=None, backend=openssl.backend)
      super().__init__(value)
      return
    except (TypeError, ValueError, exceptions.UnsupportedAlgorithm) as e:

      if "private key is encrypted" not in str(e):
        raise type_info.TypeValueError("Private key invalid: %s" % e)

      # The private key is passphrase protected, we need to see if we are
      # allowed to ask the user.
      #
      # In the case where allow_prompt was not set at all, we use the context
      # we are in to see if it makes sense to ask.
      if allow_prompt is None:
        # TODO(user): dependency loop with
        # core/grr_response_core/grr/config/client.py.
        # pylint: disable=protected-access
        if "Commandline Context" not in config_lib._CONFIG.context:
          raise type_info.TypeValueError("Private key invalid: %s" % e)
        # pylint: enable=protected-access

      # Otherwise, if allow_prompt is False, we are explicitly told that we are
      # not supposed to ask the user.
      elif not allow_prompt:
        raise type_info.TypeValueError("Private key invalid: %s" % e)

    try:
      # The private key is encrypted and we can ask the user for the passphrase.
      password = utils.PassphraseCallback()
      value = serialization.load_pem_private_key(
          initializer, password=password, backend=openssl.backend)
      super().__init__(value)
    except (TypeError, ValueError, exceptions.UnsupportedAlgorithm) as e:
      raise type_info.TypeValueError("Unable to load private key: %s" % e)

  @classmethod
  def FromHumanReadable(cls, string: Text):
    precondition.AssertType(string, Text)
    return cls.FromSerializedBytes(string.encode("ascii"))

  def GetRawPrivateKey(self):
    return self._value

  def GetPublicKey(self):
    return RSAPublicKey(self._value.public_key())

  def Sign(self, message, use_pss=False):
    """Sign a given message."""
    precondition.AssertType(message, bytes)

    # TODO(amoser): This should use PSS by default at some point.
    if not use_pss:
      padding_algorithm = padding.PKCS1v15()
    else:
      padding_algorithm = padding.PSS(
          mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH)

    return self._value.sign(message, padding_algorithm, hashes.SHA256())

  def Decrypt(self, message):
    if self._value is None:
      raise ValueError("Can't Decrypt with empty key.")

    try:
      return self._value.decrypt(
          message,
          padding.OAEP(
              mgf=padding.MGF1(algorithm=hashes.SHA1()),
              algorithm=hashes.SHA1(),
              label=None))
    except ValueError as e:
      raise CipherError(e)

  @classmethod
  def GenerateKey(cls, bits=2048, exponent=65537):
    key = rsa.generate_private_key(
        public_exponent=exponent, key_size=bits, backend=openssl.backend)
    return cls(key)

  @classmethod
  def FromSerializedBytes(cls, value: bytes):
    precondition.AssertType(value, bytes)
    return cls(value)

  @classmethod
  def FromWireFormat(cls, value):
    precondition.AssertType(value, bytes)
    return cls(value)

  def SerializeToBytes(self) -> bytes:
    if self._value is None:
      return b""
    return self._value.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption())

  def __str__(self) -> Text:
    digest = hashlib.sha256(self.AsPEM()).hexdigest()

    return "%s (%s)" % ((self.__class__).__name__, digest)

  # TODO(user): this should return a string, since PEM format
  # base64-encodes data and thus is ascii-compatible.
  def AsPEM(self):
    return self.SerializeToBytes()

  def AsPassphraseProtectedPEM(self, passphrase):
    if self._value is None:
      return ""
    return self._value.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.BestAvailableEncryption(passphrase))

  def KeyLen(self):
    if self._value is None:
      return 0
    return self._value.key_size


# TODO(amoser): Get rid of those.
# Conserve old names for backwards compatibility.
class PEMPrivateKey(RSAPrivateKey):
  pass


class PEMPublicKey(RSAPublicKey):
  pass


class Hash(rdf_structs.RDFProtoStruct):
  """A hash object containing multiple digests."""
  protobuf = jobs_pb2.Hash
  rdf_deps = [
      rdf_standard.AuthenticodeSignedData,
      rdfvalue.HashDigest,
  ]

  __hash__ = rdfvalue.RDFValue.__hash__


class SignedBlob(rdf_structs.RDFProtoStruct):
  """A signed blob.

  The client can receive and verify a signed blob (e.g. driver or executable
  binary). Once verified, the client may execute this.
  """
  protobuf = jobs_pb2.SignedBlob

  def Verify(self, public_key):
    """Verify the data in this blob.

    Args:
      public_key: The public key to use for verification.

    Returns:
      True when verification succeeds.

    Raises:
      rdfvalue.DecodeError if the data is not suitable verified.
    """
    if self.digest_type != self.HashType.SHA256:
      raise rdfvalue.DecodeError("Unsupported digest.")
    if self.signature_type not in [
        self.SignatureType.RSA_PKCS1v15, self.SignatureType.RSA_PSS
    ]:
      raise rdfvalue.DecodeError("Unsupported signature type.")

    try:
      public_key.Verify(self.data, self.signature)
    except InvalidSignature as e:
      raise rdfvalue.DecodeError("Could not verify blob. Error: %s" % e)

    return True

  def Sign(self, data, signing_key, verify_key=None):
    """Use the data to sign this blob.

    Args:
      data: String containing the blob data.
      signing_key: The key to sign with.
      verify_key: Key to verify with. If None we assume the signing key also
        contains the public key.

    Returns:
      self for call chaining.
    """

    if signing_key.KeyLen() < 2048:
      logging.warning("signing key is too short.")

    self.signature = signing_key.Sign(data)
    self.signature_type = self.SignatureType.RSA_PKCS1v15

    self.digest = hashlib.sha256(data).digest()
    self.digest_type = self.HashType.SHA256
    self.data = data

    # Test we can verify before we send it off.
    if verify_key is None:
      verify_key = signing_key.GetPublicKey()

    # Verify our own data.
    self.Verify(verify_key)

    return self


class EncryptionKey(rdfvalue.RDFPrimitive):
  """Base class for encryption keys."""

  protobuf_type = "bytes"

  def __init__(self, initializer=None):
    if initializer is None:
      super().__init__(b"")
    elif isinstance(initializer, EncryptionKey):
      super().__init__(initializer.RawBytes())
    else:
      precondition.AssertType(initializer, bytes)

      if len(initializer) % 8:
        raise CipherError("Invalid key length %d (%s)." %
                          (len(initializer) * 8, initializer))

      super().__init__(initializer)

    self.length = 8 * len(self._value)
    if 0 < self.length < 128:  # Check length if _value is not empty.
      raise CipherError("Key too short (%d): %s" % (self.length, initializer))

  @classmethod
  def FromWireFormat(cls, value):
    precondition.AssertType(value, bytes)
    return cls(value)

  @classmethod
  def FromSerializedBytes(cls, value: bytes):
    precondition.AssertType(value, bytes)
    return cls(value)

  @classmethod
  def FromHumanReadable(cls, string: Text):
    precondition.AssertType(string, Text)
    return cls(binascii.unhexlify(string))

  def __str__(self) -> Text:
    return "%s (%s)" % (self.__class__.__name__, self.AsHexDigest())

  def __len__(self) -> int:
    return len(self._value)

  def AsHexDigest(self) -> Text:
    return text.Hexify(self._value)

  def SerializeToBytes(self):
    return self._value

  @classmethod
  def GenerateKey(cls, length=128):
    return cls(os.urandom(length // 8))

  @classmethod
  def GenerateRandomIV(cls, length=128):
    return cls.GenerateKey(length=length)

  def RawBytes(self):
    return self._value


# TODO(amoser): Size is now flexible, this class makes no sense anymore.
class AES128Key(EncryptionKey):
  length = 128


class AutoGeneratedAES128Key(AES128Key):
  """Like AES128Key, but its UI edit box is prefilled with generated key."""

  def __init__(self, initializer=None, **kwargs):
    if isinstance(initializer, AES128Key):
      super().__init__(initializer=initializer.RawBytes(), **kwargs)
    else:
      super().__init__(initializer=initializer, **kwargs)


class StreamingCBCEncryptor(object):
  """A class to stream data to a CBCCipher object."""

  def __init__(self, cipher):
    self._cipher = cipher
    self._encryptor = cipher.GetEncryptor()
    self._overflow_buffer = b""
    self._block_size = len(cipher.key)

  def Update(self, data):
    data = self._overflow_buffer + data
    overflow_count = len(data) % self._block_size
    length_to_encrypt = len(data) - overflow_count
    to_encrypt = data[:length_to_encrypt]
    self._overflow_buffer = data[length_to_encrypt:]
    return self._encryptor.update(to_encrypt)

  def Finalize(self):
    res = self._encryptor.update(self._cipher.Pad(self._overflow_buffer))
    res += self._encryptor.finalize()
    return res


class AES128CBCCipher(object):
  """A Cipher using AES128 in CBC mode and PKCS7 for padding."""

  algorithm = None

  def __init__(self, key, iv):
    """Init.

    Args:
      key: The key, a rdf_crypto.EncryptionKey instance.
      iv: The iv, a rdf_crypto.EncryptionKey instance.
    """
    self.key = key.RawBytes()
    self.iv = iv.RawBytes()

  def Pad(self, data):
    padder = sym_padding.PKCS7(128).padder()
    return padder.update(data) + padder.finalize()

  def UnPad(self, padded_data):
    unpadder = sym_padding.PKCS7(128).unpadder()
    return unpadder.update(padded_data) + unpadder.finalize()

  def GetEncryptor(self):
    return ciphers.Cipher(
        algorithms.AES(self.key), modes.CBC(self.iv),
        backend=openssl.backend).encryptor()

  def Encrypt(self, data):
    """A convenience method which pads and encrypts at once."""
    encryptor = self.GetEncryptor()
    padded_data = self.Pad(data)

    try:
      return encryptor.update(padded_data) + encryptor.finalize()
    except ValueError as e:
      raise CipherError(e)

  def GetDecryptor(self):
    return ciphers.Cipher(
        algorithms.AES(self.key), modes.CBC(self.iv),
        backend=openssl.backend).decryptor()

  def Decrypt(self, data):
    """A convenience method which pads and decrypts at once."""
    decryptor = self.GetDecryptor()

    try:
      padded_data = decryptor.update(data) + decryptor.finalize()
      return self.UnPad(padded_data)
    except ValueError as e:
      raise CipherError(e)


class SymmetricCipher(rdf_structs.RDFProtoStruct):
  """Abstract symmetric cipher operations."""
  protobuf = jobs_pb2.SymmetricCipher
  rdf_deps = [
      EncryptionKey,
  ]

  @classmethod
  def Generate(cls, algorithm):
    if algorithm != cls.Algorithm.AES128CBC:
      raise RuntimeError("Algorithm not supported.")

    return cls(
        _algorithm=algorithm,
        _key=EncryptionKey.GenerateKey(length=128),
        _iv=EncryptionKey.GenerateKey(length=128))

  def _get_cipher(self):
    if self._algorithm != self.Algorithm.AES128CBC:
      raise CipherError("Unknown cipher type %s" % self._algorithm)

    return AES128CBCCipher(self._key, self._iv)

  def Encrypt(self, data):
    if self._algorithm == self.Algorithm.NONE:
      raise TypeError("Empty encryption is not allowed.")

    return self._get_cipher().Encrypt(data)

  def Decrypt(self, data):
    if self._algorithm == self.Algorithm.NONE:
      raise TypeError("Empty encryption is not allowed.")

    return self._get_cipher().Decrypt(data)


class HMAC(object):
  """A wrapper for the cryptography HMAC object."""

  def __init__(self, key, use_sha256=False):
    # We store the raw key from cryptography.io.
    if isinstance(key, EncryptionKey):
      key = key.RawBytes()

    self.key = key
    self._hmac = self._NewHMAC(use_sha256=use_sha256)

  def _NewHMAC(self, use_sha256=False):
    if use_sha256:
      hash_algorithm = hashes.SHA256()
    else:
      hash_algorithm = hashes.SHA1()
    return hmac.HMAC(self.key, hash_algorithm, backend=openssl.backend)

  def Update(self, data):
    self._hmac.update(data)

  def Finalize(self):
    return self._hmac.finalize()

  def HMAC(self, message, use_sha256=False):
    """Calculates the HMAC for a given message."""
    h = self._NewHMAC(use_sha256=use_sha256)
    h.update(message)
    return h.finalize()

  def Verify(self, message, signature):
    """Verifies the signature for a given message."""
    siglen = len(signature)
    if siglen == 20:
      hash_algorithm = hashes.SHA1()
    elif siglen == 32:
      hash_algorithm = hashes.SHA256()
    else:
      raise VerificationError("Invalid signature length %d." % siglen)

    h = hmac.HMAC(self.key, hash_algorithm, backend=openssl.backend)
    h.update(message)
    try:
      h.verify(signature)
      return True
    except exceptions.InvalidSignature as e:
      raise VerificationError(e)


class Password(rdf_structs.RDFProtoStruct):
  """A password stored in the database."""
  protobuf = jobs_pb2.Password

  def _CalculateHash(self, password, salt, iteration_count):
    kdf = pbkdf2.PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=iteration_count,
        backend=openssl.backend)
    return kdf.derive(password)

  def SetPassword(self, password):
    self.salt = b"%016x" % random.UInt64()
    self.iteration_count = 100000

    # prevent non-descriptive 'key_material must be bytes' error later
    if isinstance(password, Text):
      password = password.encode("utf-8")

    self.hashed_pwd = self._CalculateHash(password, self.salt,
                                          self.iteration_count)

  def CheckPassword(self, password):
    # prevent non-descriptive 'key_material must be bytes' error later
    if isinstance(password, Text):
      password = password.encode("utf-8")

    h = self._CalculateHash(password, self.salt, self.iteration_count)
    return constant_time.bytes_eq(h, self.hashed_pwd)
