#!/usr/bin/env python
"""Abstracts encryption and authentication."""


import hashlib
import os
import struct
import time
import zlib


from M2Crypto import BIO
from M2Crypto import EVP
from M2Crypto import m2
from M2Crypto import RSA
from M2Crypto import X509

from grr.lib import config_lib
from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib import stats
from grr.lib import type_info
from grr.lib import utils

from grr.lib.rdfvalues import flows as rdf_flows

# Constants.
ENCRYPT = 1
DECRYPT = 0


class CommunicatorInit(registry.InitHook):

  def RunOnce(self):
    """This is run only once."""
    # Counters used here
    stats.STATS.RegisterCounterMetric("grr_client_unknown")
    stats.STATS.RegisterCounterMetric("grr_decoding_error")
    stats.STATS.RegisterCounterMetric("grr_decryption_error")
    stats.STATS.RegisterCounterMetric("grr_authenticated_messages")
    stats.STATS.RegisterCounterMetric("grr_unauthenticated_messages")
    stats.STATS.RegisterCounterMetric("grr_rsa_operations")


class Error(stats.CountingExceptionMixin, Exception):
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


class PubKeyCache(object):
  """A cache of public keys for different destinations."""

  def __init__(self):
    self.pub_key_cache = utils.FastStore(max_size=50000)

  @staticmethod
  def GetCNFromCert(cert):
    subject = cert.get_subject()
    try:
      cn_id = subject.nid["CN"]
      cn = subject.get_entries_by_nid(cn_id)[0]
    except IndexError:
      raise IOError("Cert has no CN")

    return rdfvalue.RDFURN(cn.get_data().as_text())

  @staticmethod
  def PubKeyFromCert(cert):
    pub_key = cert.get_pubkey().get_rsa()
    bio = BIO.MemoryBuffer()
    pub_key.save_pub_key_bio(bio)

    return bio.read_all()

  def Flush(self):
    """Flushes the cert cache."""
    self.pub_key_cache.Flush()

  def Put(self, destination, pub_key):
    self.pub_key_cache.Put(destination, pub_key)

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
      pub_key = self.pub_key_cache.Get(common_name)
      bio = BIO.MemoryBuffer(pub_key)
      return RSA.load_pub_key_bio(bio)
    except (KeyError, X509.X509Error):
      raise KeyError("No certificate found")


class Cipher(object):
  """Holds keying information."""
  hash_function = hashlib.sha256
  hash_function_name = "sha256"
  cipher_name = "aes_128_cbc"
  key_size = 128
  iv_size = 128
  e_padding = RSA.pkcs1_oaep_padding

  # These fields get filled in by the constructor
  private_key = None
  cipher = None
  cipher_metadata = None
  encrypted_cipher = None
  encrypted_cipher_metadata = None

  def __init__(self, source, destination, private_key, pub_key_cache):
    self.private_key = private_key

    # The CipherProperties() protocol buffer specifying the session keys, that
    # we send to the other end point. It will be encrypted using the RSA private
    # key.
    self.cipher = rdf_flows.CipherProperties(
        name=self.cipher_name,
        key=os.urandom(self.key_size / 8),
        metadata_iv=os.urandom(self.iv_size / 8),
        hmac_key=os.urandom(self.key_size / 8),
        hmac_type="FULL_HMAC")

    self.pub_key_cache = pub_key_cache
    serialized_cipher = self.cipher.SerializeToString()

    self.cipher_metadata = rdf_flows.CipherMetadata(source=source)

    # Sign this cipher.
    digest = self.hash_function(serialized_cipher).digest()

    # We never want to have a password dialog
    private_key = self.private_key.GetPrivateKey()

    self.cipher_metadata.signature = private_key.sign(digest,
                                                      self.hash_function_name)

    # Now encrypt the cipher with our key
    rsa_key = pub_key_cache.GetRSAPublicKey(destination)

    stats.STATS.IncrementCounter("grr_rsa_operations")
    # M2Crypto verifies the key on each public_encrypt call which is horribly
    # slow therefore we just call the swig wrapped method directly.
    self.encrypted_cipher = m2.rsa_public_encrypt(rsa_key.rsa,
                                                  serialized_cipher,
                                                  self.e_padding)

    # Encrypt the metadata block symmetrically.
    _, self.encrypted_cipher_metadata = self.Encrypt(
        self.cipher_metadata.SerializeToString(), self.cipher.metadata_iv)

    self.signature_verified = True

  def Encrypt(self, data, iv=None):
    """Symmetrically encrypt the data using the optional iv."""
    if iv is None:
      iv = os.urandom(self.iv_size / 8)

    evp_cipher = EVP.Cipher(alg=self.cipher_name,
                            key=self.cipher.key,
                            iv=iv,
                            op=ENCRYPT)

    ctext = evp_cipher.update(data)
    ctext += evp_cipher.final()

    return iv, ctext

  def Decrypt(self, data, iv):
    """Symmetrically decrypt the data."""
    try:
      evp_cipher = EVP.Cipher(alg=self.cipher_name,
                              key=self.cipher.key,
                              iv=iv,
                              op=DECRYPT)

      text = evp_cipher.update(data)
      text += evp_cipher.final()

      return text
    except EVP.EVPError as e:
      raise DecryptionError(str(e))

  @property
  def hmac_type(self):
    return self.cipher.hmac_type

  def HMAC(self, *data):
    hmac = EVP.HMAC(self.cipher.hmac_key, algo="sha1")
    for d in data:
      hmac.update(d)

    return hmac.final()


class ReceivedCipher(Cipher):
  """A cipher which we received from our peer."""

  # Indicates if the cipher contained in the response_comms is verified.
  signature_verified = False

  # pylint: disable=super-init-not-called
  def __init__(self, response_comms, private_key, pub_key_cache):
    self.private_key = private_key
    self.pub_key_cache = pub_key_cache

    # Decrypt the message
    private_key = self.private_key.GetPrivateKey()

    try:
      # The encrypted_cipher contains the session key, iv and hmac_key.
      self.encrypted_cipher = response_comms.encrypted_cipher

      # M2Crypto verifies the key on each private_decrypt call which is horribly
      # slow therefore we just call the swig wrapped method directly.
      self.serialized_cipher = m2.rsa_private_decrypt(
          private_key.rsa, response_comms.encrypted_cipher, self.e_padding)

      # If we get here we have the session keys.
      self.cipher = rdf_flows.CipherProperties(self.serialized_cipher)

      # Check the key lengths.
      if (len(self.cipher.key) != self.key_size / 8 or
          len(self.cipher.metadata_iv) != self.iv_size / 8):
        raise DecryptionError("Invalid cipher.")

      # Check the hmac key for sanity.
      self.VerifyHMAC(response_comms)

      # Cipher_metadata contains information about the cipher - It is encrypted
      # using the symmetric session key. It contains the RSA signature of the
      # digest of the serialized CipherProperties(). It is stored inside the
      # encrypted payload.
      self.cipher_metadata = rdf_flows.CipherMetadata(self.Decrypt(
          response_comms.encrypted_cipher_metadata, self.cipher.metadata_iv))

      self.VerifyCipherSignature()

    except RSA.RSAError as e:
      raise DecryptionError(e)

  def IsEqual(self, a, b):
    """A Constant time comparison."""
    if len(a) != len(b):
      return False

    result = 0
    for x, y in zip(a, b):
      result |= ord(x) ^ ord(y)

    return result == 0

  def VerifyHMAC(self, response_comms):
    # Ensure that the hmac key is reasonable.
    if len(self.cipher.hmac_key) != self.key_size / 8:
      raise DecryptionError("Invalid cipher.")

    # Check the encrypted message integrity using HMAC.
    if self.hmac_type == "SIMPLE_HMAC":
      hmac = self.HMAC(response_comms.encrypted)
      if not self.IsEqual(hmac, response_comms.hmac):
        raise DecryptionError("HMAC verification failed.")

    elif self.hmac_type == "FULL_HMAC":
      hmac = self.HMAC(response_comms.encrypted,
                       response_comms.encrypted_cipher,
                       response_comms.encrypted_cipher_metadata,
                       response_comms.packet_iv,
                       struct.pack("<I", response_comms.api_version))

      if not self.IsEqual(hmac, response_comms.full_hmac):
        raise DecryptionError("HMAC verification failed.")

    else:
      raise DecryptionError("HMAC type no supported.")

  def VerifyCipherSignature(self):
    """Verify the signature on the encrypted cipher block."""
    if self.cipher_metadata.signature:
      digest = self.hash_function(self.serialized_cipher).digest()
      try:
        remote_public_key = self.pub_key_cache.GetRSAPublicKey(
            self.cipher_metadata.source)

        stats.STATS.IncrementCounter("grr_rsa_operations")
        if remote_public_key.verify(digest, self.cipher_metadata.signature,
                                    self.hash_function_name) == 1:
          self.signature_verified = True
        else:
          raise DecryptionError("Signature not verified by remote public key.")

      except (X509.X509Error, RSA.RSAError) as e:
        raise DecryptionError(e)

      except UnknownClientCert:
        pass


class Communicator(object):
  """A class responsible for encoding and decoding comms."""
  server_name = None

  def __init__(self, certificate=None, private_key=None):
    """Creates a communicator.

    Args:
       certificate: Our own certificate in string form (as PEM).
       private_key: Our own private key in string form (as PEM).
    """
    # A cache of cipher objects.
    self.cipher_cache = utils.TimeBasedCache(max_age=24 * 3600)
    self.private_key = private_key
    self.certificate = certificate

    # A cache for encrypted ciphers
    self.encrypted_cipher_cache = utils.FastStore(max_size=50000)

    # A cache of public keys
    self.pub_key_cache = PubKeyCache()
    self._LoadOurCertificate()

  def _LoadOurCertificate(self):
    self.cert = X509.load_cert_string(str(self.certificate))

    # Our common name
    self.common_name = PubKeyCache.GetCNFromCert(self.cert)

    # Make sure we know about our own public key
    self.pub_key_cache.Put(self.common_name,
                           self.pub_key_cache.PubKeyFromCert(self.cert))

  def EncodeMessageList(self, message_list, signed_message_list):
    """Encode the MessageList into the signed_message_list rdfvalue."""
    # By default uncompress
    uncompressed_data = message_list.SerializeToString()
    signed_message_list.message_list = uncompressed_data

    if config_lib.CONFIG["Network.compression"] == "ZCOMPRESS":
      compressed_data = zlib.compress(uncompressed_data)

      # Only compress if it buys us something.
      if len(compressed_data) < len(uncompressed_data):
        signed_message_list.compression = (
            rdf_flows.SignedMessageList.CompressionType.ZCOMPRESSION)
        signed_message_list.message_list = compressed_data

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
      raise RuntimeError("Unsupported api version: %s, expected 3." %
                         api_version)

    if destination is None:
      destination = self.server_name

    # Make a nonce for this transaction
    if timestamp is None:
      self.timestamp = timestamp = long(time.time() * 1000000)

    # Do we have a cached cipher to talk to this destination?
    try:
      cipher = self.cipher_cache.Get(destination)

    except KeyError:
      # Make a new one
      cipher = Cipher(self.common_name, destination, self.private_key,
                      self.pub_key_cache)
      self.cipher_cache.Put(destination, cipher)

    signed_message_list = rdf_flows.SignedMessageList(timestamp=timestamp)
    self.EncodeMessageList(message_list, signed_message_list)

    result.encrypted_cipher_metadata = cipher.encrypted_cipher_metadata

    # Include the encrypted cipher.
    result.encrypted_cipher = cipher.encrypted_cipher

    serialized_message_list = signed_message_list.SerializeToString()

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
                                   result.packet_iv,
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
       a Signed_Message_List rdfvalue
    """
    try:
      response_comms = rdf_flows.ClientCommunication(encrypted_response)
      return self.DecodeMessages(response_comms)
    except (rdfvalue.DecodeError, type_info.TypeValueError, ValueError,
            AttributeError) as e:
      raise DecodingError("Protobuf parsing error: %s" % e)

  def DecompressMessageList(self, signed_message_list):
    """Decompress the message data from signed_message_list.

    Args:
      signed_message_list: A SignedMessageList rdfvalue with some data in it.

    Returns:
      a MessageList rdfvalue.

    Raises:
      DecodingError: If decompression fails.
    """
    compression = signed_message_list.compression
    if compression == rdf_flows.SignedMessageList.CompressionType.UNCOMPRESSED:
      data = signed_message_list.message_list

    elif (compression ==
          rdf_flows.SignedMessageList.CompressionType.ZCOMPRESSION):
      try:
        data = zlib.decompress(signed_message_list.message_list)
      except zlib.error as e:
        raise DecodingError("Failed to decompress: %s" % e)
    else:
      raise DecodingError("Compression scheme not supported")

    try:
      result = rdf_flows.MessageList(data)
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
    if response_comms.api_version not in [3]:
      raise DecryptionError("Unsupported api version: %s, expected 3." %
                            response_comms.api_version)

    if response_comms.encrypted_cipher:
      # Have we seen this cipher before?
      try:
        cipher = self.encrypted_cipher_cache.Get(
            response_comms.encrypted_cipher)
      except KeyError:
        cipher = ReceivedCipher(response_comms, self.private_key,
                                self.pub_key_cache)

        if cipher.signature_verified:
          # Remember it for next time.
          self.encrypted_cipher_cache.Put(response_comms.encrypted_cipher,
                                          cipher)

      # Verify the cipher HMAC with the new response_comms. This will raise
      # DecryptionError if the HMAC does not agree.
      cipher.VerifyHMAC(response_comms)

      # Decrypt the message with the per packet IV.
      plain = cipher.Decrypt(response_comms.encrypted, response_comms.packet_iv)
      try:
        signed_message_list = rdf_flows.SignedMessageList(plain)
      except rdfvalue.DecodeError as e:
        raise DecryptionError(str(e))

      message_list = self.DecompressMessageList(signed_message_list)

    else:
      # The message is not encrypted. We do not allow unencrypted
      # messages:
      raise DecryptionError("Server response is not encrypted.")

    # Are these messages authenticated?
    auth_state = self.VerifyMessageSignature(response_comms,
                                             signed_message_list, cipher,
                                             response_comms.api_version)

    # Mark messages as authenticated and where they came from.
    for msg in message_list.job:
      msg.auth_state = auth_state
      msg.source = cipher.cipher_metadata.source

    return (message_list.job, cipher.cipher_metadata.source,
            signed_message_list.timestamp)

  def VerifyMessageSignature(self, unused_response_comms, signed_message_list,
                             cipher, api_version):
    """Verify the message list signature.

    This is the way the messages are verified in the client.

    In the client we also check that the nonce returned by the server is correct
    (the timestamp doubles as a nonce). If the nonce fails we deem the response
    unauthenticated since it might have resulted from a replay attack.

    Args:
       signed_message_list: The SignedMessageList rdfvalue from the server.
       cipher: The cipher belonging to the remote end.
       api_version: The api version we should use.

    Returns:
       a rdf_flows.GrrMessage.AuthorizationState.

    Raises:
       DecryptionError: if the message is corrupt.
    """
    # This is not used atm since we only support a single api version (3).
    _ = api_version
    result = rdf_flows.GrrMessage.AuthorizationState.UNAUTHENTICATED

    # Give the cipher another chance to check its signature.
    if not cipher.signature_verified:
      cipher.VerifyCipherSignature()

    if cipher.signature_verified:
      stats.STATS.IncrementCounter("grr_authenticated_messages")
      result = rdf_flows.GrrMessage.AuthorizationState.AUTHENTICATED

    # Check for replay attacks. We expect the server to return the same
    # timestamp nonce we sent.
    if signed_message_list.timestamp != self.timestamp:
      result = rdf_flows.GrrMessage.AuthorizationState.UNAUTHENTICATED

    if not cipher.cipher_metadata:
      # Fake the metadata
      cipher.cipher_metadata = rdf_flows.CipherMetadata(
          source=signed_message_list.source)

    return result
