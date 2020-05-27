#!/usr/bin/env python
# Lint as: python3
"""Abstracts encryption and authentication."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import abc
import struct
import time
import zlib

from grr_response_core.lib import communicator
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import type_info
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.stats import metrics


Error = communicator.Error
DecodingError = communicator.Error
DecryptionError = communicator.DecryptionError
LegacyClientDecryptionError = communicator.LegacyClientDecryptionError

GRR_CLIENT_RECEIVED_BYTES = metrics.Counter("grr_client_received_bytes")
GRR_CLIENT_SENT_BYTES = metrics.Counter("grr_client_sent_bytes")


class UnknownServerCertError(DecodingError):
  """Raised when the client key is not retrieved."""


class Communicator(metaclass=abc.ABCMeta):
  """A class responsible for encoding and decoding comms."""
  server_name = None
  common_name = None

  def __init__(self, certificate=None, private_key=None):
    """Creates a communicator.

    Args:
       certificate: Our own certificate.
       private_key: Our own private key.
    """
    self.private_key = private_key
    self.certificate = certificate
    self._ClearServerCipherCache()

  def _ClearServerCipherCache(self):
    self.server_cipher = None
    self.server_cipher_age = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(0)

  @abc.abstractmethod
  def _GetRemotePublicKey(self, server_name):
    raise NotImplementedError()

  @classmethod
  def EncodeMessageList(cls, message_list, packed_message_list):
    """Encode the MessageList into the packed_message_list rdfvalue."""
    # By default uncompress
    uncompressed_data = message_list.SerializeToBytes()
    packed_message_list.message_list = uncompressed_data

    compressed_data = zlib.compress(uncompressed_data)

    # Only compress if it buys us something.
    if len(compressed_data) < len(uncompressed_data):
      packed_message_list.compression = (
          rdf_flows.PackedMessageList.CompressionType.ZCOMPRESSION)
      packed_message_list.message_list = compressed_data

  def _GetServerCipher(self):
    """Returns the cipher for self.server_name."""

    if self.server_cipher is not None:
      expiry = self.server_cipher_age + rdfvalue.Duration.From(1, rdfvalue.DAYS)
      if expiry > rdfvalue.RDFDatetime.Now():
        return self.server_cipher

    remote_public_key = self._GetRemotePublicKey(self.server_name)
    self.server_cipher = communicator.Cipher(self.common_name, self.private_key,
                                             remote_public_key)
    self.server_cipher_age = rdfvalue.RDFDatetime.Now()
    return self.server_cipher

  def EncodeMessages(self,
                     message_list,
                     result,
                     timestamp=None,
                     api_version=3):
    """Accepts a list of messages and encodes for transmission.

    This function signs and then encrypts the payload.

    Args:
       message_list: A MessageList rdfvalue containing a list of GrrMessages.
       result: A ClientCommunication rdfvalue which will be filled in.
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
    cipher = self._GetServerCipher()

    # Make a nonce for this transaction
    if timestamp is None:
      self.timestamp = timestamp = int(time.time() * 1000000)

    packed_message_list = rdf_flows.PackedMessageList(timestamp=timestamp)
    self.EncodeMessageList(message_list, packed_message_list)

    result.encrypted_cipher_metadata = cipher.encrypted_cipher_metadata

    # Include the encrypted cipher.
    result.encrypted_cipher = cipher.encrypted_cipher

    serialized_message_list = packed_message_list.SerializeToBytes()

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
                                   result.packet_iv.SerializeToBytes(),
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
      response_comms = rdf_flows.ClientCommunication.FromSerializedBytes(
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
      result = rdf_flows.MessageList.FromSerializedBytes(data)
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
    cipher = communicator.ReceivedCipher(response_comms, self.private_key)

    source = cipher.GetSource()
    try:
      remote_public_key = self._GetRemotePublicKey(source)
      if cipher.VerifyCipherSignature(remote_public_key):
        cipher_verified = True

    except UnknownServerCertError:
      # We don't know who we are talking to.
      remote_public_key = None

    # Decrypt the message with the per packet IV.
    plain = cipher.Decrypt(response_comms.encrypted, response_comms.packet_iv)
    try:
      packed_message_list = rdf_flows.PackedMessageList.FromSerializedBytes(
          plain)
    except rdfvalue.DecodeError as e:
      raise DecryptionError(e)

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
      result = rdf_flows.GrrMessage.AuthorizationState.AUTHENTICATED

    # Check for replay attacks. We expect the server to return the same
    # timestamp nonce we sent.
    if packed_message_list.timestamp != self.timestamp:  # pytype: disable=attribute-error
      result = rdf_flows.GrrMessage.AuthorizationState.UNAUTHENTICATED

    if not cipher.cipher_metadata:
      # Fake the metadata
      cipher.cipher_metadata = rdf_flows.CipherMetadata(
          source=packed_message_list.source)

    return result
