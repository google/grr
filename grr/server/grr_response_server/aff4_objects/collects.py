#!/usr/bin/env python
"""Implementations of various collections."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import io

from builtins import range  # pylint: disable=redefined-builtin

from grr_response_core.lib.rdfvalues import crypto as rdf_crypto
from grr_response_server import aff4
from grr_response_server import data_store
from grr_response_server import grr_collections


class GRRSignedBlob(aff4.AFF4Stream):
  """A container for storing a signed binary blob such as a driver."""

  collection = None

  @classmethod
  def NewFromContent(cls,
                     content,
                     urn,
                     chunk_size=1024,
                     token=None,
                     private_key=None,
                     public_key=None):
    """Alternate constructor for GRRSignedBlob.

    Creates a GRRSignedBlob from a content string by chunking it and signing
    each chunk.

    Args:
      content: The data to stored in the GRRSignedBlob.
      urn: The AFF4 URN to create.

      chunk_size: Data will be chunked into this size (each chunk is
        individually signed.
      token: The ACL Token.
      private_key: An rdf_crypto.RSAPrivateKey() instance.
      public_key: An rdf_crypto.RSAPublicKey() instance.

    Returns:
      the URN of the new object written.
    """
    aff4.FACTORY.Delete(urn, token=token)
    with data_store.DB.GetMutationPool() as pool:
      with aff4.FACTORY.Create(
          urn, cls, mode="w", mutation_pool=pool, token=token) as fd:
        for start_of_chunk in range(0, len(content), chunk_size):
          chunk = content[start_of_chunk:start_of_chunk + chunk_size]
          blob_rdf = rdf_crypto.SignedBlob()
          blob_rdf.Sign(chunk, private_key, public_key)
          fd.Add(blob_rdf, mutation_pool=pool)

    return urn

  @property
  def size(self):
    self._EnsureInitialized()
    return self._size

  @size.setter
  def size(self, value):
    self._size = value

  @property
  def chunks(self):
    """Returns the total number of chunks."""
    self._EnsureInitialized()
    return len(self.collection)

  def _EnsureInitialized(self):
    if self.collection is None:

      self.collection = grr_collections.SignedBlobCollection(
          self.urn.Add("collection"))
      self.fd = io.BytesIO()
      self._size = 0

      if self.mode == "r":
        for x in self.collection:
          self.fd.write(x.data)

        self._size = self.fd.tell()
        self.fd.seek(0)
      elif self.mode != "w":
        raise RuntimeError(
            "GRRSignedBlob can not be opened in mixed (rw) mode.")

  def Write(self, length):
    raise IOError("GRRSignedBlob is not writable. Please use "
                  "NewFromContent() to create a new GRRSignedBlob.")

  def Read(self, length):
    if self.mode != "r":
      raise IOError("Reading GRRSignedBlob opened for writing.")

    self._EnsureInitialized()
    return self.fd.read(length)

  def Add(self, item, mutation_pool=None):
    if "r" in self.mode:
      raise IOError("GRRSignedBlob does not support appending.")
    if mutation_pool is None:
      raise ValueError("Mutation pool can't be none.")
    self._EnsureInitialized()
    self.collection.Add(item, mutation_pool=mutation_pool)

  def __iter__(self):
    self._EnsureInitialized()
    return iter(self.collection)

  def __len__(self):
    return self.size

  def Tell(self):
    self._EnsureInitialized()
    return self.fd.tell()

  def Seek(self, offset, whence=0):
    self._EnsureInitialized()
    self.fd.seek(offset, whence)

  def OnDelete(self, deletion_pool=None):
    super(GRRSignedBlob, self).OnDelete(deletion_pool=deletion_pool)

    self._EnsureInitialized()
    self.collection.Delete()
