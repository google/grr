#!/usr/bin/env python
"""Mixin tests for blobs in the relational db."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from builtins import range  # pylint: disable=redefined-builtin
from builtins import zip  # pylint: disable=redefined-builtin

from grr_response_server.rdfvalues import objects as rdf_objects


class DatabaseTestBlobsMixin(object):
  """An abstract class for testing db.Database implementations.

  This mixin adds methods to test the blobs handling.
  """

  def testReadingNonExistentBlobReturnsNone(self):
    d = self.db

    blob_id = rdf_objects.BlobID(b"01234567" * 4)
    result = d.ReadBlobs([blob_id])
    self.assertEqual(result, {blob_id: None})

  def testSingleBlobCanBeWrittenAndThenRead(self):
    d = self.db

    blob_id = rdf_objects.BlobID(b"01234567" * 4)
    blob_data = b"abcdef"

    d.WriteBlobs({blob_id: blob_data})

    result = d.ReadBlobs([blob_id])
    self.assertEqual(result, {blob_id: blob_data})

  def testMultipleBlobsCanBeWrittenAndThenRead(self):
    d = self.db

    blob_ids = [rdf_objects.BlobID((b"%d1234567" % i) * 4) for i in range(10)]
    blob_data = [b"a" * i for i in range(10)]

    d.WriteBlobs(dict(zip(blob_ids, blob_data)))

    result = d.ReadBlobs(blob_ids)
    self.assertEqual(result, dict(zip(blob_ids, blob_data)))

  def testWriting80MbOfBlobsWithSingleCallWorks(self):
    d = self.db

    num_blobs = 80
    blob_ids = [
        rdf_objects.BlobID((b"%02d234567" % i) * 4) for i in range(num_blobs)
    ]
    blob_data = [b"a" * 1024 * 1024] * num_blobs

    d.WriteBlobs(dict(zip(blob_ids, blob_data)))

    result = d.ReadBlobs(blob_ids)
    self.assertEqual(result, dict(zip(blob_ids, blob_data)))

  def testCheckBlobsExistCorrectlyReportsPresentAndMissingBlobs(self):
    d = self.db

    blob_id = rdf_objects.BlobID(b"01234567" * 4)
    blob_data = b"abcdef"

    d.WriteBlobs({blob_id: blob_data})

    other_blob_id = rdf_objects.BlobID(b"abcdefgh" * 4)
    result = d.CheckBlobsExist([blob_id, other_blob_id])
    self.assertEqual(result, {blob_id: True, other_blob_id: False})

  def testHashBlobReferenceCanBeWrittenAndReadBack(self):
    d = self.db

    blob_ref = rdf_objects.BlobReference(
        offset=0, size=42, blob_id=rdf_objects.BlobID(b"01234567" * 4))
    hash_id = rdf_objects.SHA256HashID(b"0a1b2c3d" * 4)

    data = {hash_id: [blob_ref]}
    d.WriteHashBlobReferences(data)

    results = d.ReadHashBlobReferences([hash_id])
    self.assertEqual(results, data)

  def testReportsNonExistingHashesAsNone(self):
    d = self.db

    hash_id = rdf_objects.SHA256HashID(b"0a1b2c3d" * 4)

    results = d.ReadHashBlobReferences([hash_id])
    self.assertEqual(results, {hash_id: None})

  def testCorrectlyHandlesRequestWithOneExistingAndOneMissingHash(self):
    d = self.db

    blob_ref = rdf_objects.BlobReference(
        offset=0, size=42, blob_id=rdf_objects.BlobID(b"01234567" * 4))
    hash_id = rdf_objects.SHA256HashID(b"0a1b2c3d" * 4)

    d.WriteHashBlobReferences({hash_id: [blob_ref]})

    missing_hash_id = rdf_objects.SHA256HashID(b"00000000" * 4)

    results = d.ReadHashBlobReferences([missing_hash_id, hash_id])
    self.assertEqual(results, {
        hash_id: [blob_ref],
        missing_hash_id: None,
    })

  def testMultipleHashBlobReferencesCanBeWrittenAndReadBack(self):
    d = self.db

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
    d.WriteHashBlobReferences(data)

    results = d.ReadHashBlobReferences([hash_id_1, hash_id_2])
    self.assertEqual(results, data)

    results = d.ReadHashBlobReferences([hash_id_1])
    self.assertEqual(results, {hash_id_1: data[hash_id_1]})

    results = d.ReadHashBlobReferences([hash_id_2])
    self.assertEqual(results, {hash_id_2: data[hash_id_2]})
