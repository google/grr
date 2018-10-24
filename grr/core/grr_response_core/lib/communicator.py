#!/usr/bin/env python
"""Abstracts encryption and authentication."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import abc
import struct
import time
import zlib


from future.utils import with_metaclass

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import type_info
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import crypto as rdf_crypto
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.stats import stats_collector_instance
from grr_response_core.stats import stats_utils


# TODO(user): Move this to server_metrics.py after server and client
# Communicators have been decoupled. These metrics should not be tracked on
# the client.
def GetMetricMetadata():
  """Returns a list of MetricMetadata for communicator-related metrics."""
  return [
      stats_utils.CreateCounterMetadata("grr_client_unknown"),
      stats_utils.CreateCounterMetadata("grr_decoding_error"),
      stats_utils.CreateCounterMetadata("grr_decryption_error"),
      stats_utils.CreateCounterMetadata("grr_authenticated_messages"),
      stats_utils.CreateCounterMetadata("grr_unauthenticated_messages"),
      stats_utils.CreateCounterMetadata("grr_rsa_operations"),
      stats_utils.CreateCounterMetadata(
          "grr_encrypted_cipher_cache", fields=[("type", str)]),
  ]


class Error(stats_utils.CountingExceptionMixin, Exception):
  """Base class for all exceptions in this module."""
  pass


class DecodingError(Error):
  """Raised when the message failed to decrypt or decompress."""
  counter = "grr_decoding_error"


class DecryptionError(DecodingError):
  """Raised when the message can not be decrypted properly."""
  counter = "grr_decryption_error"


class UnknownClientCert(DecodingError):
  """Raised when the client key is not retrieved."""
  counter = "grr_client_unknown"


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

    serialized_cipher = self.cipher.SerializeToString()

    self.cipher_metadata = rdf_flows.CipherMetadata(source=source)

    # Sign this cipher.
    self.cipher_metadata.signature = self.private_key.Sign(serialized_cipher)

    # Now encrypt the cipher.
    stats_collector_instance.Get().IncrementCounter("grr_rsa_operations")
    self.encrypted_cipher = remote_public_key.Encrypt(serialized_cipher)

    # Encrypt the metadata block symmetrically.
    _, self.encrypted_cipher_metadata = self.Encrypt(
        self.cipher_metadata.SerializeToString(), self.cipher.metadata_iv)

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
      self.cipher = rdf_flows.CipherProperties.FromSerializedString(
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
      self.cipher_metadata = rdf_flows.CipherMetadata.FromSerializedString(
          serialized_metadata)

    except (rdf_crypto.InvalidSignature, rdf_crypto.CipherError) as e:
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
          comms.packet_iv.SerializeToString(),
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

      stats_collector_instance.Get().IncrementCounter("grr_rsa_operations")
      remote_public_key.Verify(self.serialized_cipher,
                               self.cipher_metadata.signature)
      return True


# TODO(user):pytype Communicator inherits abc.ABCMeta, but type checker
# can't infer this, apparently because with_metaclass is used.
# pytype: disable=ignored-abstractmethod
class Communicator(with_metaclass(abc.ABCMeta, object)):
  """A class responsible for encoding and decoding comms."""
  server_name = None

  def __init__(self, certificate=None, private_key=None):
    """Creates a communicator.

    Args:
       certificate: Our own certificate.
       private_key: Our own private key.
    """
    self.private_key = private_key
    self.certificate = certificate
    self._ClearServerCipherCache()

    # A cache for encrypted ciphers
    self.encrypted_cipher_cache = utils.FastStore(max_size=50000)

  @abc.abstractmethod
  def _GetRemotePublicKey(self, server_name):
    raise NotImplementedError()

  @classmethod
  def EncodeMessageList(cls, message_list, packed_message_list):
    """Encode the MessageList into the packed_message_list rdfvalue."""
    # By default uncompress
    uncompressed_data = message_list.SerializeToString()
    packed_message_list.message_list = uncompressed_data

    compressed_data = zlib.compress(uncompressed_data)

    # Only compress if it buys us something.
    if len(compressed_data) < len(uncompressed_data):
      packed_message_list.compression = (
          rdf_flows.PackedMessageList.CompressionType.ZCOMPRESSION)
      packed_message_list.message_list = compressed_data

  def _ClearServerCipherCache(self):
    self.server_cipher = None
    self.server_cipher_age = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(0)

  def _GetServerCipher(self):
    """Returns the cipher for self.server_name."""

    if self.server_cipher is not None:
      expiry = self.server_cipher_age + rdfvalue.Duration("1d")
      if expiry > rdfvalue.RDFDatetime.Now():
        return self.server_cipher

    remote_public_key = self._GetRemotePublicKey(self.server_name)
    self.server_cipher = Cipher(self.common_name, self.private_key,
                                remote_public_key)
    self.server_cipher_age = rdfvalue.RDFDatetime.Now()
    return self.server_cipher

  def EncodeMessages(self,
                     message_list,
                     result,
                     destination=None,
                     timestamp=None,
                     api_version=3):
    """Accepts a list of messages and encodes for transmission.

    This function signs and then encrypts the payload.

    Args:
       message_list: A MessageList rdfvalue containing a list of
       GrrMessages.

       result: A ClientCommunication rdfvalue which will be filled in.

       destination: The CN of the remote system this should go to.

       timestamp: A timestamp to use for the signed messages. If None - use the
              current time.

       api_version: The api version which this should be encoded in.

    Returns:
       A nonce (based on time) which is inserted to the encrypted payload. The
       client can verify that the server is able to decrypt the message and
       return the nonce.

    Raises:
       RuntimeError: If we do not support this api version.
    """
    if api_version not in [3]:
      raise RuntimeError(
          "Unsupported api version: %s, expected 3." % api_version)
    # TODO(amoser): This is actually not great, we have two
    # communicator classes already, one for the client, one for the
    # server. This should be different methods, not a single one that
    # gets passed a destination (server side) or not (client side).
    if destination is None:
      destination = self.server_name
      # For the client it makes sense to cache the server cipher since
      # it's the only cipher it ever uses.
      cipher = self._GetServerCipher()
    else:
      remote_public_key = self._GetRemotePublicKey(destination)
      cipher = Cipher(self.common_name, self.private_key, remote_public_key)

    # Make a nonce for this transaction
    if timestamp is None:
      self.timestamp = timestamp = int(time.time() * 1000000)

    packed_message_list = rdf_flows.PackedMessageList(timestamp=timestamp)
    self.EncodeMessageList(message_list, packed_message_list)

    result.encrypted_cipher_metadata = cipher.encrypted_cipher_metadata

    # Include the encrypted cipher.
    result.encrypted_cipher = cipher.encrypted_cipher

    serialized_message_list = packed_message_list.SerializeToString()

    # Encrypt the message symmetrically.
    # New scheme cipher is signed plus hmac over message list.
    result.packet_iv, result.encrypted = cipher.Encrypt(serialized_message_list)

    # This is to support older endpoints.
    result.hmac = cipher.HMAC(result.encrypted)

    # Newer endpoints only look at this HMAC. It is recalculated for each packet
    # in the session. Note that encrypted_cipher and encrypted_cipher_metadata
    # do not change between all packets in this session.
    result.full_hmac = cipher.HMAC(result.encrypted, result.encrypted_cipher,
                                   result.encrypted_cipher_metadata,
                                   result.packet_iv.SerializeToString(),
                                   struct.pack("<I", api_version))

    result.api_version = api_version

    if isinstance(result, rdfvalue.RDFValue):
      # Store the number of messages contained.
      result.num_messages = len(message_list)

    return timestamp

  def DecryptMessage(self, encrypted_response):
    """Decrypt the serialized, encrypted string.

    Args:
       encrypted_response: A serialized and encrypted string.

    Returns:
       a Packed_Message_List rdfvalue
    """
    try:
      response_comms = rdf_flows.ClientCommunication.FromSerializedString(
          encrypted_response)
      return self.DecodeMessages(response_comms)
    except (rdfvalue.DecodeError, type_info.TypeValueError, ValueError,
            AttributeError) as e:
      raise DecodingError("Error while decrypting messages: %s" % e)

  @classmethod
  def DecompressMessageList(cls, packed_message_list):
    """Decompress the message data from packed_message_list.

    Args:
      packed_message_list: A PackedMessageList rdfvalue with some data in it.

    Returns:
      a MessageList rdfvalue.

    Raises:
      DecodingError: If decompression fails.
    """
    compression = packed_message_list.compression
    if compression == rdf_flows.PackedMessageList.CompressionType.UNCOMPRESSED:
      data = packed_message_list.message_list

    elif (compression ==
          rdf_flows.PackedMessageList.CompressionType.ZCOMPRESSION):
      try:
        data = zlib.decompress(packed_message_list.message_list)
      except zlib.error as e:
        raise DecodingError("Failed to decompress: %s" % e)
    else:
      raise DecodingError("Compression scheme not supported")

    try:
      result = rdf_flows.MessageList.FromSerializedString(data)
    except rdfvalue.DecodeError:
      raise DecodingError("RDFValue parsing failed.")

    return result

  def DecodeMessages(self, response_comms):
    """Extract and verify server message.

    Args:
        response_comms: A ClientCommunication rdfvalue

    Returns:
       list of messages and the CN where they came from.

    Raises:
       DecryptionError: If the message failed to decrypt properly.
    """
    # Have we seen this cipher before?
    cipher_verified = False
    try:
      cipher = self.encrypted_cipher_cache.Get(response_comms.encrypted_cipher)
      stats_collector_instance.Get().IncrementCounter(
          "grr_encrypted_cipher_cache", fields=["hits"])

      # Even though we have seen this encrypted cipher already, we should still
      # make sure that all the other fields are sane and verify the HMAC.
      cipher.VerifyReceivedHMAC(response_comms)
      cipher_verified = True

      # If we have the cipher in the cache, we know the source and
      # should have a corresponding public key.
      source = cipher.GetSource()
      remote_public_key = self._GetRemotePublicKey(source)
    except KeyError:
      stats_collector_instance.Get().IncrementCounter(
          "grr_encrypted_cipher_cache", fields=["misses"])
      cipher = ReceivedCipher(response_comms, self.private_key)

      source = cipher.GetSource()
      try:
        remote_public_key = self._GetRemotePublicKey(source)
        if cipher.VerifyCipherSignature(remote_public_key):
          # At this point we know this cipher is legit, we can cache it.
          self.encrypted_cipher_cache.Put(response_comms.encrypted_cipher,
                                          cipher)
          cipher_verified = True

      except UnknownClientCert:
        # We don't know who we are talking to.
        remote_public_key = None

    # Decrypt the message with the per packet IV.
    plain = cipher.Decrypt(response_comms.encrypted, response_comms.packet_iv)
    try:
      packed_message_list = rdf_flows.PackedMessageList.FromSerializedString(
          plain)
    except rdfvalue.DecodeError as e:
      raise DecryptionError(str(e))

    message_list = self.DecompressMessageList(packed_message_list)

    # Are these messages authenticated?
    # pyformat: disable
    auth_state = self.VerifyMessageSignature(
        response_comms,
        packed_message_list,
        cipher,
        cipher_verified,
        response_comms.api_version,
        remote_public_key)
    # pyformat: enable

    # Mark messages as authenticated and where they came from.
    for msg in message_list.job:
      msg.auth_state = auth_state
      msg.source = cipher.cipher_metadata.source

    return (message_list.job, cipher.cipher_metadata.source,
            packed_message_list.timestamp)

  def VerifyMessageSignature(self, unused_response_comms, packed_message_list,
                             cipher, cipher_verified, api_version,
                             remote_public_key):
    """Verify the message list signature.

    This is the way the messages are verified in the client.

    In the client we also check that the nonce returned by the server is correct
    (the timestamp doubles as a nonce). If the nonce fails we deem the response
    unauthenticated since it might have resulted from a replay attack.

    Args:
      packed_message_list: The PackedMessageList rdfvalue from the server.
      cipher: The cipher belonging to the remote end.
      cipher_verified: If True, the cipher's signature is not verified again.
      api_version: The api version we should use.
      remote_public_key: The public key of the source.
    Returns:
      An rdf_flows.GrrMessage.AuthorizationState.

    Raises:
       DecryptionError: if the message is corrupt.
    """
    # This is not used atm since we only support a single api version (3).
    _ = api_version
    result = rdf_flows.GrrMessage.AuthorizationState.UNAUTHENTICATED

    if cipher_verified or cipher.VerifyCipherSignature(remote_public_key):
      stats_collector_instance.Get().IncrementCounter(
          "grr_authenticated_messages")
      result = rdf_flows.GrrMessage.AuthorizationState.AUTHENTICATED

    # Check for replay attacks. We expect the server to return the same
    # timestamp nonce we sent.
    if packed_message_list.timestamp != self.timestamp:
      result = rdf_flows.GrrMessage.AuthorizationState.UNAUTHENTICATED

    if not cipher.cipher_metadata:
      # Fake the metadata
      cipher.cipher_metadata = rdf_flows.CipherMetadata(
          source=packed_message_list.source)

    return result


# pytype: enable=ignored-abstractmethod
