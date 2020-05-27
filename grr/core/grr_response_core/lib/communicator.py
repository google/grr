#!/usr/bin/env python
# Lint as: python3
"""Abstracts encryption and authentication."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import struct

from grr_response_core.lib.rdfvalues import crypto as rdf_crypto
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.stats import metrics


# Although these metrics are never queried on the client, removing them from the
# client code seems not worth the effort.
GRR_DECODING_ERROR = metrics.Counter("grr_decoding_error")
GRR_DECRYPTION_ERROR = metrics.Counter("grr_decryption_error")
GRR_LEGACY_CLIENT_DECRYPTION_ERROR = metrics.Counter(
    "grr_legacy_client_decryption_error")
GRR_RSA_OPERATIONS = metrics.Counter("grr_rsa_operations")


class Error(Exception):
  """Base class for all exceptions in this module."""


class DecodingError(Error):
  """Raised when the message failed to decrypt or decompress."""

  @GRR_DECODING_ERROR.Counted()
  def __init__(self, message):
    super().__init__(message)


class DecryptionError(DecodingError):
  """Raised when the message can not be decrypted properly."""

  @GRR_DECRYPTION_ERROR.Counted()
  def __init__(self, message):
    super().__init__(message)


class LegacyClientDecryptionError(DecryptionError):
  """Raised when old clients' messages cannot be decrypted."""

  @GRR_LEGACY_CLIENT_DECRYPTION_ERROR.Counted()
  def __init__(self, message):
    super().__init__(message)


class Cipher(object):
  """Holds keying information."""
  cipher_name = "aes_128_cbc"
  key_size = 128
  iv_size = 128

  # These fields get filled in by the constructor
  private_key = None
  cipher = None
  cipher_metadata = None
  encrypted_cipher = None
  encrypted_cipher_metadata = None

  def __init__(self, source, private_key, remote_public_key):
    self.private_key = private_key

    # The CipherProperties() protocol buffer specifying the session keys, that
    # we send to the other end point. It will be encrypted using the RSA private
    # key.
    self.cipher = rdf_flows.CipherProperties(
        name=self.cipher_name,
        key=rdf_crypto.EncryptionKey.GenerateKey(length=self.key_size),
        metadata_iv=rdf_crypto.EncryptionKey.GenerateKey(length=self.key_size),
        hmac_key=rdf_crypto.EncryptionKey.GenerateKey(length=self.key_size),
        hmac_type="FULL_HMAC")

    serialized_cipher = self.cipher.SerializeToBytes()

    self.cipher_metadata = rdf_flows.CipherMetadata(source=source)

    # Sign this cipher.
    self.cipher_metadata.signature = self.private_key.Sign(serialized_cipher)

    # Now encrypt the cipher.
    GRR_RSA_OPERATIONS.Increment()
    self.encrypted_cipher = remote_public_key.Encrypt(serialized_cipher)

    # Encrypt the metadata block symmetrically.
    _, self.encrypted_cipher_metadata = self.Encrypt(
        self.cipher_metadata.SerializeToBytes(), self.cipher.metadata_iv)

  def Encrypt(self, data, iv=None):
    """Symmetrically encrypt the data using the optional iv."""
    if iv is None:
      iv = rdf_crypto.EncryptionKey.GenerateKey(length=128)
    cipher = rdf_crypto.AES128CBCCipher(self.cipher.key, iv)
    return iv, cipher.Encrypt(data)

  def Decrypt(self, data, iv):
    """Symmetrically decrypt the data."""
    key = rdf_crypto.EncryptionKey(self.cipher.key)
    iv = rdf_crypto.EncryptionKey(iv)
    return rdf_crypto.AES128CBCCipher(key, iv).Decrypt(data)

  @property
  def hmac_type(self):
    return self.cipher.hmac_type

  def HMAC(self, *data):
    return rdf_crypto.HMAC(self.cipher.hmac_key).HMAC(b"".join(data))


class ReceivedCipher(Cipher):
  """A cipher which we received from our peer."""

  # pylint: disable=super-init-not-called
  def __init__(self, response_comms, private_key):
    self.private_key = private_key
    self.response_comms = response_comms

    if response_comms.api_version not in [3]:
      raise DecryptionError("Unsupported api version: %s, expected 3." %
                            response_comms.api_version)

    if not response_comms.encrypted_cipher:
      # The message is not encrypted. We do not allow unencrypted
      # messages:
      raise DecryptionError("Server response is not encrypted.")

    try:
      # The encrypted_cipher contains the session key, iv and hmac_key.
      self.serialized_cipher = private_key.Decrypt(
          response_comms.encrypted_cipher)

      # If we get here we have the session keys.
      self.cipher = rdf_flows.CipherProperties.FromSerializedBytes(
          self.serialized_cipher)

      # Check the key lengths.
      if (len(self.cipher.key) * 8 != self.key_size or
          len(self.cipher.metadata_iv) * 8 != self.iv_size or
          len(self.cipher.hmac_key) * 8 != self.key_size):
        raise DecryptionError("Invalid cipher.")

      self.VerifyHMAC()

      # Cipher_metadata contains information about the cipher - It is encrypted
      # using the symmetric session key. It contains the RSA signature of the
      # digest of the serialized CipherProperties(). It is stored inside the
      # encrypted payload.
      serialized_metadata = self.Decrypt(
          response_comms.encrypted_cipher_metadata, self.cipher.metadata_iv)
      self.cipher_metadata = rdf_flows.CipherMetadata.FromSerializedBytes(
          serialized_metadata)

    except (rdf_crypto.InvalidSignature, rdf_crypto.CipherError) as e:
      if "Ciphertext length must be equal to key size" in str(e):
        raise LegacyClientDecryptionError(e)
      else:
        raise DecryptionError(e)

  def GetSource(self):
    return self.cipher_metadata.source

  def VerifyReceivedHMAC(self, comms):
    """Verifies a received HMAC.

    This method raises a DecryptionError if the received HMAC does not
    verify. If the HMAC verifies correctly, True is returned.

    Args:
      comms: The comms RdfValue to verify.

    Raises:
      DecryptionError: The HMAC did not verify.

    Returns:
      True
    """
    return self._VerifyHMAC(comms)

  def VerifyHMAC(self):
    """Verifies the HMAC of self.response.comms.

    This method raises a DecryptionError if the received HMAC does not
    verify. If the HMAC verifies correctly, True is returned.

    Raises:
      DecryptionError: The HMAC did not verify.

    Returns:
      True

    """
    return self._VerifyHMAC(self.response_comms)

  def _VerifyHMAC(self, comms=None):
    """Verifies the HMAC.

    This method raises a DecryptionError if the received HMAC does not
    verify. If the HMAC verifies correctly, True is returned.

    Args:
      comms: The comms RdfValue to verify.

    Raises:
      DecryptionError: The HMAC did not verify.

    Returns:
      True

    """
    # Check the encrypted message integrity using HMAC.
    if self.hmac_type == "SIMPLE_HMAC":
      msg = comms.encrypted
      digest = comms.hmac
    elif self.hmac_type == "FULL_HMAC":
      msg = b"".join([
          comms.encrypted, comms.encrypted_cipher,
          comms.encrypted_cipher_metadata,
          comms.packet_iv.SerializeToBytes(),
          struct.pack("<I", comms.api_version)
      ])
      digest = comms.full_hmac
    else:
      raise DecryptionError("HMAC type no supported.")

    try:
      rdf_crypto.HMAC(self.cipher.hmac_key).Verify(msg, digest)
    except rdf_crypto.VerificationError as e:
      raise DecryptionError("HMAC verification failed: %s" % e)

    return True

  def VerifyCipherSignature(self, remote_public_key):
    """Verifies the signature on the encrypted cipher block.

    This method returns True if the signature verifies correctly with
    the key given.

    Args:
      remote_public_key: The remote public key.

    Returns:
      None
    Raises:
      rdf_crypto.VerificationError: A signature and a key were both given but
                                    verification fails.

    """
    if self.cipher_metadata.signature and remote_public_key:
      GRR_RSA_OPERATIONS.Increment()
      remote_public_key.Verify(self.serialized_cipher,
                               self.cipher_metadata.signature)
      return True
