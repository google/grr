#!/usr/bin/env python
"""Mixin that tests hash blob references."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_server.rdfvalues import objects as rdf_objects


class DatabaseTestBlobReferencesMixin(object):
  """A mixin that provides tests for hash blob references."""

  def testHashBlobReferenceCanBeWrittenAndReadBack(self):
    blob_ref = rdf_objects.BlobReference(
        offset=0, size=42, blob_id=rdf_objects.BlobID(b"01234567" * 4))
    hash_id = rdf_objects.SHA256HashID(b"0a1b2c3d" * 4)

    data = {hash_id: [blob_ref]}
    self.db.WriteHashBlobReferences(data)

    results = self.db.ReadHashBlobReferences([hash_id])
    self.assertEqual(results, data)

  def testReportsNonExistingHashesAsNone(self):
    hash_id = rdf_objects.SHA256HashID(b"0a1b2c3d" * 4)

    results = self.db.ReadHashBlobReferences([hash_id])
    self.assertEqual(results, {hash_id: None})

  def testCorrectlyHandlesRequestWithOneExistingAndOneMissingHash(self):
    blob_ref = rdf_objects.BlobReference(
        offset=0, size=42, blob_id=rdf_objects.BlobID(b"01234567" * 4))
    hash_id = rdf_objects.SHA256HashID(b"0a1b2c3d" * 4)

    self.db.WriteHashBlobReferences({hash_id: [blob_ref]})

    missing_hash_id = rdf_objects.SHA256HashID(b"00000000" * 4)

    results = self.db.ReadHashBlobReferences([missing_hash_id, hash_id])
    self.assertEqual(results, {
        hash_id: [blob_ref],
        missing_hash_id: None,
    })

  def testMultipleHashBlobReferencesCanBeWrittenAndReadBack(self):
    blob_ref_1 = rdf_objects.BlobReference(
        offset=0, size=42, blob_id=rdf_objects.BlobID(b"01234567" * 4))
    blob_ref_2 = rdf_objects.BlobReference(
        offset=42, size=42, blob_id=rdf_objects.BlobID(b"01234568" * 4))

    hash_id_1 = rdf_objects.SHA256HashID(b"0a1b2c3d" * 4)
    hash_id_2 = rdf_objects.SHA256HashID(b"0a1b2c3e" * 4)

    data = {
        hash_id_1: [blob_ref_1],
        hash_id_2: [blob_ref_1, blob_ref_2],
    }
    self.db.WriteHashBlobReferences(data)

    results = self.db.ReadHashBlobReferences([hash_id_1, hash_id_2])
    self.assertEqual(results, data)

    results = self.db.ReadHashBlobReferences([hash_id_1])
    self.assertEqual(results, {hash_id_1: data[hash_id_1]})

    results = self.db.ReadHashBlobReferences([hash_id_2])
    self.assertEqual(results, {hash_id_2: data[hash_id_2]})


# This file is a test library and thus does not require a __main__ block.
