#!/usr/bin/env python
"""A module with test cases for blob encryption key methods."""
import os

from grr_response_server.databases import db as abstract_db
from grr_response_server.rdfvalues import objects as rdf_objects


class DatabaseTestBlobKeysMixin:
  """A mixin class for testing blob encryption keys database methods."""
  db: abstract_db.Database

  # This is test-only module, we don't need docstrings for test methods.
  # pylint: disable=missing-function-docstring

  # This is a test mixin but there is no way to specify this with type system,
  # so we have to make pytype close an eye on this.
  # pytype: disable=attribute-error

  def testWriteBlobEncryptionKeysEmpty(self):
    self.db.WriteBlobEncryptionKeys({})  # Should not fail.

  def testReadBlobEncryptionKeysEmpty(self):
    results = self.db.ReadBlobEncryptionKeys([])  # Should not fail.
    self.assertEmpty(results)

  def testReadBlobEncryptionKeysNonExistent(self):
    blob_id = rdf_objects.BlobID(os.urandom(32))

    results = self.db.ReadBlobEncryptionKeys([blob_id])
    self.assertEqual(results, {blob_id: None})

  def testReadBlobEncryptionKeysSingle(self):
    blob_id = rdf_objects.BlobID(os.urandom(32))
    key = abstract_db.EncryptionKey(key_id="foo", nonce=os.urandom(12))

    self.db.WriteBlobEncryptionKeys({blob_id: key})

    results = self.db.ReadBlobEncryptionKeys([blob_id])
    self.assertEqual(results, {blob_id: key})

  def testReadBlobEncryptionKeysMultiple(self):
    blob_id_1 = rdf_objects.BlobID(os.urandom(32))
    blob_id_2 = rdf_objects.BlobID(os.urandom(32))
    blob_id_3 = rdf_objects.BlobID(os.urandom(32))

    key_1 = abstract_db.EncryptionKey(key_id="foo", nonce=os.urandom(12))
    key_2 = abstract_db.EncryptionKey(key_id="bar", nonce=os.urandom(12))
    key_3 = abstract_db.EncryptionKey(key_id="qux", nonce=os.urandom(12))

    self.db.WriteBlobEncryptionKeys({
        blob_id_1: key_1,
        blob_id_2: key_2,
        blob_id_3: key_3,
    })

    results = self.db.ReadBlobEncryptionKeys([blob_id_1, blob_id_2, blob_id_3])
    self.assertEqual(results, {
        blob_id_1: key_1,
        blob_id_2: key_2,
        blob_id_3: key_3,
    })

  def testReadBlobEncryptionKeysOverridden(self):
    blob_id = rdf_objects.BlobID(os.urandom(32))

    key_1 = abstract_db.EncryptionKey(key_id="foo", nonce=os.urandom(12))
    self.db.WriteBlobEncryptionKeys({blob_id: key_1})

    results = self.db.ReadBlobEncryptionKeys([blob_id])
    self.assertEqual(results[blob_id], key_1)

    key_2 = abstract_db.EncryptionKey(key_id="bar", nonce=os.urandom(12))
    self.db.WriteBlobEncryptionKeys({blob_id: key_2})

    results = self.db.ReadBlobEncryptionKeys([blob_id])
    self.assertEqual(results[blob_id], key_2)

    key_3 = abstract_db.EncryptionKey(key_id="baz", nonce=os.urandom(12))
    self.db.WriteBlobEncryptionKeys({blob_id: key_3})

    results = self.db.ReadBlobEncryptionKeys([blob_id])
    self.assertEqual(results[blob_id], key_3)

  # pytype: enable=attribute-error
