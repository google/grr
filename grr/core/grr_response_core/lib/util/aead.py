#!/usr/bin/env python
"""A module with utilities for AEAD streams."""

from collections.abc import Iterator
import io
import itertools
import os
import struct
from typing import IO

from cryptography.hazmat.primitives.ciphers import aead

from grr_response_core.lib.util import io as ioutil
from grr_response_core.lib.util import iterator


def Encrypt(stream: IO[bytes], key: bytes) -> IO[bytes]:
  """Encrypts given file-like object using AES algorithm with GCM mode.

  The input stream is divided into small chunks of predefined size and then each
  chunk is encrypted using AES GCM procedure. In the encoded stream, before each
  proper chunk there is a nonce binary string prepended. As associated data for
  each encrypted chunk, chunk index and information about whether it is the last
  chunk is used.

  Args:
    stream: A file-like object to encrypt.
    key: A secret key used for encrypting the data.

  Returns:
    A file-like object with encrypted data.
  """
  aesgcm = aead.AESGCM(key)

  def Generate() -> Iterator[bytes]:
    chunks = ioutil.Chunk(stream, size=_AEAD_CHUNK_SIZE)
    chunks = iterator.Lookahead(enumerate(chunks))

    for idx, chunk in chunks:
      nonce = os.urandom(_AEAD_NONCE_SIZE)
      adata = _AEAD_ADATA_FORMAT.pack(idx, chunks.done)

      yield nonce + aesgcm.encrypt(nonce, chunk, adata)

  return ioutil.Unchunk(Generate())


def Decrypt(stream: IO[bytes], key: bytes) -> IO[bytes]:
  """Decrypts given file-like object using AES algorithm in GCM mode.

  Refer to the encryption documentation to learn about the details of the format
  that this function allows to decode.

  Args:
    stream: A file-like object to decrypt.
    key: A secret key used for decrypting the data.

  Returns:
    A file-like object with decrypted data.
  """
  aesgcm = aead.AESGCM(key)

  def Generate() -> Iterator[bytes]:
    # Buffered reader should accept `IO[bytes]` but for now it accepts only
    # `RawIOBase` (which is a concrete base class for all I/O implementations).
    reader = io.BufferedReader(stream)  # pytype: disable=wrong-arg-types

    # We abort early if there is no data in the stream. Otherwise we would try
    # to read nonce and fail.
    if not reader.peek():
      return

    for idx in itertools.count():
      nonce = reader.read(_AEAD_NONCE_SIZE)

      # As long there is some data in the buffer (and there should be because of
      # the initial check) there should be a fixed-size nonce prepended to each
      # chunk.
      if len(nonce) != _AEAD_NONCE_SIZE:
        raise EOFError(f"Incorrect nonce length: {len(nonce)}")

      chunk = reader.read(_AEAD_CHUNK_SIZE + 16)

      # `BufferedReader#peek` will return non-empty byte string if there is more
      # data available in the stream.
      is_last = reader.peek() == b""  # pylint: disable=g-explicit-bool-comparison

      adata = _AEAD_ADATA_FORMAT.pack(idx, is_last)

      yield aesgcm.decrypt(nonce, chunk, adata)

      if is_last:
        break

  return ioutil.Unchunk(Generate())


# We use 12 bytes (96 bits) as it is the recommended IV length by NIST for best
# performance [1]. See AESGCM documentation for more details.
#
# [1]: https://csrc.nist.gov/publications/detail/sp/800-38d/final
_AEAD_NONCE_SIZE = 12

# Because chunk size is crucial to the security of the whole procedure, we don't
# let users pick their own chunk size. Instead, we use a fixed-size chunks of
# 4 mebibytes.
_AEAD_CHUNK_SIZE = 4 * 1024 * 1024

# As associated data for each encrypted chunk we use an integer denoting chunk
# id followed by a byte with information whether this is the last chunk.
_AEAD_ADATA_FORMAT = struct.Struct("!Q?")
