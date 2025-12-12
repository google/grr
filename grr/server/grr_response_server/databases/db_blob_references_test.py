#!/usr/bin/env python
"""Mixin that tests hash blob references."""

import os
import random

from grr_response_proto import objects_pb2
from grr_response_server.rdfvalues import objects as rdf_objects


class DatabaseTestBlobReferencesMixin(object):
  """A mixin that provides tests for hash blob references."""

  def testWriteHashBlobReferences_Empty(self):
    self.db.WriteHashBlobReferences({
        rdf_objects.SHA256HashID.FromData(b""): [],
    })

  def testWriteHashblobReferences_None(self):
    self.db.WriteHashBlobReferences({})

  def testHashBlobReferenceCanBeWrittenAndReadBack(self):
    blob_ref = objects_pb2.BlobReference(
        offset=0, size=42, blob_id=(b"01234567" * 4)
    )
    hash_id = rdf_objects.SHA256HashID(b"0a1b2c3d" * 4)

    data = {hash_id: [blob_ref]}
    self.db.WriteHashBlobReferences(data)

    results = self.db.ReadHashBlobReferences([hash_id])
    self.assertEqual(results, data)

  def testReportsNonExistingHashesAsNone(self):
    hash_id = rdf_objects.SHA256HashID(b"0a1b2c3d" * 4)

    results = self.db.ReadHashBlobReferences([hash_id])
    self.assertEqual(results, {hash_id: None})

  def testReadHashBlobReferencesWithEmptyInput(self):

    results = self.db.ReadHashBlobReferences([])
    self.assertEqual(results, {})

  def testCorrectlyHandlesRequestWithOneExistingAndOneMissingHash(self):
    blob_ref = objects_pb2.BlobReference(
        offset=0, size=42, blob_id=(b"01234567" * 4)
    )
    hash_id = rdf_objects.SHA256HashID(b"0a1b2c3d" * 4)

    self.db.WriteHashBlobReferences({hash_id: [blob_ref]})

    missing_hash_id = rdf_objects.SHA256HashID(b"00000000" * 4)

    results = self.db.ReadHashBlobReferences([missing_hash_id, hash_id])
    self.assertEqual(
        results,
        {
            hash_id: [blob_ref],
            missing_hash_id: None,
        },
    )

  def testMultipleHashBlobReferencesCanBeWrittenAndReadBack(self):
    blob_ref_1 = objects_pb2.BlobReference(
        offset=0, size=42, blob_id=(b"01234567" * 4)
    )
    blob_ref_2 = objects_pb2.BlobReference(
        offset=42, size=42, blob_id=(b"01234568" * 4)
    )

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

  def testWriteHashBlobHandlesLargeAmountsOfData(self):
    hash_id_blob_refs = {}

    for _ in range(50000):
      hash_id = rdf_objects.SHA256HashID(os.urandom(32))

      blob_ref = objects_pb2.BlobReference()
      blob_ref.blob_id = os.urandom(32)
      blob_ref.offset = random.randint(0, 1024 * 1024 * 1024)
      blob_ref.size = random.randint(128, 256)

      hash_id_blob_refs[hash_id] = [blob_ref]

    self.db.WriteHashBlobReferences(hash_id_blob_refs)

    hash_ids = list(hash_id_blob_refs.keys())
    read_hash_id_blob_refs = self.db.ReadHashBlobReferences(hash_ids)
    self.assertEqual(read_hash_id_blob_refs, hash_id_blob_refs)


# This file is a test library and thus does not require a __main__ block.
