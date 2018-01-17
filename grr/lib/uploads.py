#!/usr/bin/env python
"""Manage file uploads."""
import collections
import gzip
import hashlib
import StringIO
import struct
import sys
import zlib


from grr.lib.rdfvalues import crypto
from grr.lib.rdfvalues import flows
from grr.lib.rdfvalues import structs as rdf_structs

from grr_response_proto import jobs_pb2

# The header struct format.
HEADER_MAGIC = "GRR\x01"
PART_TYPE_ENCRYPTED_CIPHER = 1
PART_TYPE_ENCRYPTED_DATA = 2
HEADER_FMT = "4sIHIIIII"
HEADER_SIZE = struct.calcsize(HEADER_FMT)
EncryptedHeader = collections.namedtuple(
    "EncryptedHeader",
    [
        "Magic",  # HEADER_MAGIC
        "Version",  # Header Version.
        "PartType",  # One of PART_TYPE_*
        "PartLength",  # Length of entire part including header.
        "HMACStart",  # Offset of where the HMAC begins.
        "HMACLength",  # Length of HMAC.
        "DataStart",  # Offset where the part data begins.
        "DataLength",  # Length of data.
    ])


class SignaturePart(rdf_structs.RDFProtoStruct):
  """A Signature part."""
  protobuf = jobs_pb2.SignaturePart


class EncryptStream(object):
  """A file like object which encrypts and signs another stream."""

  def __init__(self,
               readers_public_key,
               writers_private_key,
               fd,
               chunk_size=1024 * 1024):
    """Constructor.

    Args:

      readers_public_key: The public key of the destined reader of this
        stream. The stream will be encrypted with the readers public key.
      writers_private_key: The private_key of the writer of this stream. Data
        will be signed using this private key.
      fd: A file like object we read from.
      chunk_size: This will be the size of the parts.
    """
    self.fd = fd
    self.readers_public_key = readers_public_key
    self.writers_private_key = writers_private_key
    self.chunk_size = chunk_size

    # Prepare the initial header.
    self.cipher_properties = flows.CipherProperties.GetInializedKeys()
    self.cipher = crypto.AES128CBCCipher(self.cipher_properties.key,
                                         self.cipher_properties.metadata_iv)
    self.hmac = crypto.HMAC(self.cipher_properties.hmac_key.RawBytes())

    serialized_cipher = self.cipher_properties.SerializeToString()
    signature = SignaturePart(
        encrypted_cipher=readers_public_key.Encrypt(serialized_cipher),
        signature=writers_private_key.Sign(serialized_cipher))

    # First part is the encrypted cipher.
    self.encrypted_buffer = BufferedReader()
    self.encrypted_buffer.write(
        self._GetPart(signature.SerializeToString(),
                      PART_TYPE_ENCRYPTED_CIPHER))
    self.eof = False

  def _GetPart(self, data, data_type):
    """Create a new part."""
    # Calculate a HMAC over the entire part.
    hmac = self.hmac.HMAC(data)
    header = EncryptedHeader(
        Magic=HEADER_MAGIC,
        Version=1,
        PartType=data_type,
        DataStart=HEADER_SIZE,
        DataLength=len(data),
        HMACStart=HEADER_SIZE + len(data),
        HMACLength=len(hmac),
        PartLength=HEADER_SIZE + len(hmac) + len(data))
    return struct.pack(HEADER_FMT, *header) + data + hmac

  def read(self, length):  # pylint: disable=invalid-name
    """Read length bytes from the stream."""
    if length is None:
      raise RuntimeError("Read calls must be bounded.")

    if self.eof:
      return ""

    while self.encrypted_buffer.len < length:
      current_chunk = self._EncryptNextChunk()
      # None indicates that the input stream is exhausted.
      if current_chunk is None:
        self.eof = True
        break

      self.encrypted_buffer.write(current_chunk)

    return self.encrypted_buffer.ReadFromFront(length)

  def Read(self, length):
    return self.read(length)

  def _EncryptNextChunk(self):
    """Encrypt a new chunk to send."""
    data = self.fd.read(self.chunk_size)
    if not data:
      return None

    # Send an encrypted data part.
    encrypted_data = self.cipher.Encrypt(data)
    return self._GetPart(encrypted_data, PART_TYPE_ENCRYPTED_DATA)

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    return self.close()


class DecryptStream(object):
  """A file like object which decrypts another stream.

  This wrapper is designed to be inserted in the write() path of another
  stream. It will collect all parts written into it and in turn write those to
  the wrapped stream.

  """

  def __init__(self, readers_private_key, writers_public_key, outfd):
    """Constructor.

    Args:
      readers_private_key: The private key of the destined reader of this
        stream. The stream will be decrypted with the readers private key.
      writers_public_key: The public_key of the writer of this stream. Data's
        signature will be verified using this public key.
      outfd: A file like object we write to. This must be opened for writing.
    """
    self.outfd = outfd
    self.readers_private_key = readers_private_key
    self.writers_public_key = writers_public_key
    self.header = None
    self.part_end = None
    self.buffer = BufferedReader()
    self.cipher = None

  def Write(self, data):
    """Write some data into the stream."""
    self.buffer.write(data)

    while 1:
      # We are looking for the next part header.
      if self.part_end is None:
        # Not enough data to process a part.
        if self.buffer.len < HEADER_SIZE:
          return

        # Parse the header.
        packed_header = self.buffer.getvalue()[:HEADER_SIZE]
        self.header = EncryptedHeader(*struct.unpack(HEADER_FMT, packed_header))
        if self.header.Magic != HEADER_MAGIC or self.header.Version != 1:
          raise IOError("Invalid header.")

        # We need to wait until we have this much data in the buffer.
        self.part_end = self.header.PartLength

      # We do not have a full part yet.
      if self.buffer.len < self.part_end:
        return

      self._ProcessPart()

  def _ProcessPart(self):
    """Process a full part in the buffer.

    We assume a complete part exists in self.buffer.

    Raises:
      IOError: if there is anything wrong with the data.
    """
    payload_data = self.buffer.getvalue()[
        self.header.DataStart:self.header.DataStart + self.header.DataLength]

    payload_hmac = self.buffer.getvalue()[
        self.header.HMACStart:self.header.HMACStart + self.header.HMACLength]

    # Now process the part.
    # First header - we need to initialize the cipher.
    if self.cipher is None:
      if self.header.PartType != PART_TYPE_ENCRYPTED_CIPHER:
        raise IOError("First part must be ENCRYPTED_CIPHER")

      signature = SignaturePart.FromSerializedString(payload_data)
      decrypted_cipher = self.readers_private_key.Decrypt(
          signature.encrypted_cipher)

      # Verify its signature.
      self.writers_public_key.Verify(decrypted_cipher, signature.signature)

      self.cipher_properties = flows.CipherProperties.FromSerializedString(
          decrypted_cipher)

      self.cipher = self.cipher_properties.GetCipher()
      self.hmac = self.cipher_properties.GetHMAC()

    # The part contains data.
    elif self.header.PartType == PART_TYPE_ENCRYPTED_DATA:
      plain_text = self.cipher.Decrypt(payload_data)
      self.outfd.write(plain_text)

    else:
      raise IOError("Unsupported part type %s" % self.header.PartType)

    try:
      # Make sure the hmac is correct.
      self.hmac.Verify(payload_data, payload_hmac)
    except crypto.VerificationError:
      raise IOError("HMAC not verified")

    # Remove the part from the buffer.
    self.buffer.ReadFromFront(self.part_end)
    self.part_end = None

  def Close(self):
    if self.buffer.len > 0:
      raise IOError("Partial Message Received")
    self.flush()
    self.outfd.close()

  def Flush(self):
    self.outfd.flush()

  close = Close
  flush = Flush
  write = Write

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    return self.close()


class BufferedReader(StringIO.StringIO):
  """A FLO which can be written to the back and read from the front."""

  def ReadFromFront(self, length):
    result_data = self.getvalue()
    self.truncate(0)
    self.write(result_data[length:])
    return result_data[:length]


class GzipWrapper(object):
  """Wraps a file like object and compresses it."""
  BUFFER_SIZE = 1024 * 1024

  def __init__(self, infd, byte_limit=None):
    self.total_read = 0
    self.infd = infd
    self.buff_fd = BufferedReader()
    self.zipper = gzip.GzipFile(mode="wb", fileobj=self.buff_fd)
    self.remaining_bytes = byte_limit
    if self.remaining_bytes is None:
      self.remaining_bytes = sys.maxint

    self.hashers = {
        "sha256": hashlib.sha256(),
        "sha1": hashlib.sha1(),
        "md5": hashlib.md5()
    }

  def Read(self, length=10000000):
    """Public read interface.

    Readers from this endpoint will receive a gzip file streamed from the infd.

    Args:
      length: How many bytes to read.

    Returns:
      A string.
    """

    # Read infd until we have length available in self.buff_fd.
    while self.zipper and self.buff_fd.len < length:
      data = self.infd.read(min(self.remaining_bytes, self.BUFFER_SIZE))
      if not data and self.zipper:
        # infd is finished.
        self.zipper.flush()
        self.zipper.close()
        self.zipper = None
        break

      l = len(data)
      self.total_read += l
      self.remaining_bytes -= l
      for h in self.hashers.values():
        h.update(data)
      self.zipper.write(data)

    return self.buff_fd.ReadFromFront(length)

  read = Read

  def __iter__(self):
    while 1:
      data = self.read(self.BUFFER_SIZE)
      if not data:
        break

      yield data

  def HashObject(self):
    return crypto.Hash(
        sha256=self.hashers["sha256"].digest(),
        sha1=self.hashers["sha1"].digest(),
        md5=self.hashers["md5"].digest())


class GunzipWrapper(object):
  """Wraps a file like object and decompresses it."""
  BUFFER_SIZE = 1024 * 1024

  def __init__(self, outfd):
    self.outfd = outfd
    # 16 + zlib.MAX_WBITS indicates that we want to decompress a gzip
    # compressed stream. See
    # http://stackoverflow.com/questions/1838699/
    # how-can-i-decompress-a-gzip-stream-with-zlib.
    self.decompressor = zlib.decompressobj(16 + zlib.MAX_WBITS)

  def Write(self, data):
    self.outfd.write(self.decompressor.decompress(data))

  def Flush(self):
    self.outfd.flush()

  def Close(self):
    self.outfd.close()

  write = Write
  flush = Flush
  close = Close
