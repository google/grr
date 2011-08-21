#!/usr/bin/env python

# Copyright 2010 Google Inc.
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


"""Abstracts encryption and authentication."""


import hashlib
import time
import zlib


from M2Crypto import BIO
from M2Crypto import EVP
from M2Crypto import Rand
from M2Crypto import RSA
from M2Crypto import X509

from grr.client import conf as flags
from google.protobuf import message
import logging
from grr.lib import stats
from grr.lib import utils
from grr.proto import jobs_pb2

flags.DEFINE_string("compression", default="ZCOMPRESS",
                    help="Type of compression (ZCOMPRESS, UNCOMPRESSED)")

FLAGS = flags.FLAGS

# Constants.
ENCRYPT = 1
DECRYPT = 0

# Initialize the PRNG.
Rand.rand_seed(Rand.rand_bytes(1000))


# Counters used here
stats.STATS.grr_client_unknown = 0
stats.STATS.grr_authenticated_messages = 0
stats.STATS.grr_unauthenticated_messages = 0


# These actually are inherited from Exception
class DecodingError(stats.CountingException):
  """Raised when the message failed to decrypt or decompress."""
  counter = "grr_decoding_error"


class DecryptionError(DecodingError):
  """Raised when the message can not be decrypted properly."""
  counter = "grr_decryption_error"


class UnknownClientCert(DecodingError):
  """Raised when the client key is not retrieved."""
  counter = "grr_client_unknown"


class Communicator(object):
  """A class responsible for encoding and decoding comms."""
  hash_function = hashlib.sha256
  hash_function_name = "sha256"
  cipher = "aes_128_cbc"
  key_size = 128
  iv_size = 128
  e_padding = RSA.pkcs1_oaep_padding
  server_name = None

  def __init__(self, certificate):
    """Creates a communicator.

    Args:
       certificate: Our own certificate and key in string form. If
         this is not specified we send unsigned packets.
    """
    self.pub_key_cache = utils.FastStore(100)
    self._LoadOurCertificate(certificate)

  def _LoadOurCertificate(self, certificate):
    self.cert = X509.load_cert_string(certificate)

    # This is our private key - make sure it has no password set.
    self.private_key = certificate

    # Make sure its valid
    RSA.load_key_string(certificate, callback=lambda x: "")

    # Our common name
    self.common_name = self._GetCNFromCert(self.cert)

  def _GetCNFromCert(self, cert):
    subject = cert.get_subject()
    try:
      cn_id = subject.nid["CN"]
      cn = subject.get_entries_by_nid(cn_id)[0]
    except IndexError:
      raise IOError("Cert has no CN")

    return cn.get_data().as_text()

  def FlushCache(self):
    """Flushes the cert cache."""
    self.pub_key_cache.Flush()

  def GetRSAPublicKey(self, common_name="Server"):
    """Retrieve the relevant public key for that common name.

    This maintains a cache of public keys or loads them from external
    sources if available.

    Args:
      common_name: The common_name of the key we need.

    Returns:
      A valid public key.
    """
    try:
      bio = BIO.MemoryBuffer(self.pub_key_cache.Get(common_name))
      return RSA.load_pub_key_bio(bio)
    except (KeyError, X509.X509Error):
      raise IOError("No certificate found")

  def EncodeMessageList(self, message_list, signed_message_list):
    """Encode the MessageList proto into the signed_message_list proto."""
    # By default uncompress
    uncompressed_data = message_list.SerializeToString()
    signed_message_list.message_list = uncompressed_data

    if FLAGS.compression == "ZCOMPRESS":
      compressed_data = zlib.compress(uncompressed_data)

      # Only compress if it buys us something.
      if len(compressed_data) < len(uncompressed_data):
        signed_message_list.compression = jobs_pb2.SignedMessageList.ZCOMPRESSION
        signed_message_list.message_list = compressed_data

  def EncodeMessages(self, message_list, result, destination=None,
                     timestamp=None):
    """Accepts a list of messages and encodes for transmission.

    This function signs and then encrypts the payload.

    Args:
       message_list: A MessageList protobuf containing a list of
       GrrMessages.

       result: A ClientCommunication protobuf which will be filled in.

       destination: The CN of the remote system this should go to.

       timestamp: A timestamp to use for the signed messages. If None - use the
              current time.

    Returns:
       A nonce (based on time) which is inserted to the encrypted payload. The
       client can verify that the server is able to decrypt the message and
       return the nonce.
    """
    if destination is None:
      destination = self.server_name

    # Make a nonce for this transaction
    if timestamp is None:
      self.timestamp = timestamp = long(time.time() * 1000000)

    signed_message_list = jobs_pb2.SignedMessageList(timestamp=timestamp)
    self.EncodeMessageList(message_list, signed_message_list)
    signed_message_list.source = self.common_name

    ## Now we want to sign the message list
    digest = self.hash_function(signed_message_list.message_list).digest()

    # We never want to have a password dialog
    private_key = RSA.load_key_string(self.private_key, callback=lambda x: "")
    signed_message_list.signature = private_key.sign(
        digest, self.hash_function_name)

    rsa_key = self.GetRSAPublicKey(destination)

    # Now prepare the cipher
    cipher_properties = jobs_pb2.CipherProperties(
        name=self.cipher,
        key=Rand.rand_pseudo_bytes(self.key_size / 8)[0],
        iv=Rand.rand_pseudo_bytes(self.iv_size / 8)[0]
        )

    # Encrypt the message
    cipher = EVP.Cipher(alg=self.cipher,
                        key=cipher_properties.key,
                        iv=cipher_properties.iv,
                        op=ENCRYPT)

    ctext = cipher.update(signed_message_list.SerializeToString())
    ctext += cipher.final()

    # Send the cipher properties encrypted with the public key
    result.encrypted_cipher = rsa_key.public_encrypt(
        cipher_properties.SerializeToString(),
        self.e_padding)

    result.encrypted = ctext

    return timestamp

  def DecryptMessage(self, encrypted_response):
    """Decrypt the serialized, encrypted string.

    Args:
       encrypted_response: A serialized and encrypted string.

    Returns:
       a Signed_Message_List protobuf
    """
    response_comms = jobs_pb2.ClientCommunication()
    response_comms.ParseFromString(encrypted_response)

    return self.DecodeMessages(response_comms)

  def DecompressMessageList(self, signed_message_list):
    """Decompress the message data from signed_message_list.

    Args:
      signed_message_list: A SignedMessageList proto with some data in it.

    Returns:
      a MessageList proto.

    Raises:
      DecodingError: If decompression fails.
    """
    compression = signed_message_list.compression
    if compression == jobs_pb2.SignedMessageList.UNCOMPRESSED:
      data = signed_message_list.message_list

    elif compression == jobs_pb2.SignedMessageList.ZCOMPRESSION:
      try:
        data = zlib.decompress(signed_message_list.message_list)
      except zlib.error, e:
        raise DecodingError("Failed to decompress: %s" % e)
    else:
      raise DecodingError("Compression scheme not supported")

    try:
      result = jobs_pb2.MessageList()
      result.ParseFromString(data)
    except message.DecodeError:
      raise DecodingError("Proto parsing failed.")

    return result

  def DecodeMessages(self, response_comms):
    """Extract and verify server message.

    Args:
        response_comms: A ClientCommunication protobuf

    Returns:
       list of messages and the CN where they came from.

    Raises:
       DecryptionError: If the message failed to decrypt properly.
    """
    if response_comms.encrypted_cipher:
      # Decrypt the message
      private_key = RSA.load_key_string(self.private_key, callback=lambda x: "")

      cipher_properties = jobs_pb2.CipherProperties()
      cipher_properties.ParseFromString(
          private_key.private_decrypt(
              response_comms.encrypted_cipher,
              self.e_padding
              )
          )

      # Add entropy to the PRNG.
      Rand.rand_add(cipher_properties.iv, len(cipher_properties.iv)/2)

      # Check the key lengths.
      if (len(cipher_properties.key) != self.key_size / 8 or
          len(cipher_properties.iv) != self.iv_size / 8):
        raise DecryptionError("Decryption failed.")

      # Get the right cipher keyed by the received keys
      cipher = EVP.Cipher(alg=self.cipher,
                          key=cipher_properties.key,
                          iv=cipher_properties.iv,
                          op=DECRYPT)
      ptext = cipher.update(response_comms.encrypted)
      ptext += cipher.final()
    else:
      # The message is not encrypted. We do not allow unencrypted
      # messages:
      raise DecryptionError("Server response is not encrypted.")

    signed_message_list = jobs_pb2.SignedMessageList()
    signed_message_list.ParseFromString(ptext)

    message_list = self.DecompressMessageList(signed_message_list)

    # Are these messages authenticated?
    auth_state = self.VerifyMessageSignature(signed_message_list)
    # Mark messages as authenticated and where they came from.
    for msg in message_list.job:
      msg.auth_state = auth_state
      msg.source = signed_message_list.source

    return (message_list.job, signed_message_list.source,
            signed_message_list.timestamp)

  def VerifyMessageSignature(self, signed_message_list):
    """Verify the message list signature.

    In the client we also check that the nonce returned by the server is correct
    (the timestamp doubles as a nonce). If the nonce fails we deem the response
    unauthenticated since it might have resulted from a replay attack.

    Args:
       signed_message_list: The SignedMessageList proto from the server.

    Returns:
       a jobs_pb2.GrrMessage.AuthorizationState.
    """

    # messages are not authenticated
    auth_state = jobs_pb2.GrrMessage.UNAUTHENTICATED

    if signed_message_list.signature:
      # Verify the incoming message.
      digest = self.hash_function(signed_message_list.message_list).digest()

      if signed_message_list.timestamp == self.timestamp:
        # This will raise if the key fails to be fetched.
        remote_public_key = self.GetRSAPublicKey(signed_message_list.source)
        remote_public_key.verify(digest, signed_message_list.signature,
                                 self.hash_function_name)

        auth_state = jobs_pb2.GrrMessage.AUTHENTICATED
        stats.STATS.grr_authenticated_messages += 1

    return auth_state
