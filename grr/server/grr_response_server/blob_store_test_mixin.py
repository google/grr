#!/usr/bin/env python
"""Mixin class to be used in tests for BlobStore implementations."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import abc

from future.utils import with_metaclass

from grr_response_server import blob_store
from grr_response_server.rdfvalues import objects as rdf_objects


class BlobStoreTestMixin(with_metaclass(abc.ABCMeta)):
  """Mixin providing tests shared by all blob store tests implementations."""

  @abc.abstractmethod
  def CreateBlobStore(self):
    """Create a test blob store.

    Returns:
      A pair (blob_store, cleanup), where blob_store is an instance of
      blob_store.BlobStore to be tested  and cleanup is a function which
      destroys blob_store, releasing any resources held by it.
    """

  def setUp(self):
    super(BlobStoreTestMixin, self).setUp()
    bs, self.cleanup = self.CreateBlobStore()
    self.blob_store = blob_store.BlobStoreValidationWrapper(bs)

  def tearDown(self):
    if self.cleanup:
      self.cleanup()
    super(BlobStoreTestMixin, self).tearDown()

  def testReadingNonExistentBlobReturnsNone(self):
    blob_id = rdf_objects.BlobID(b"01234567" * 4)
    result = self.blob_store.ReadBlobs([blob_id])
    self.assertEqual(result, {blob_id: None})

  def testSingleBlobCanBeWrittenAndThenRead(self):
    blob_id = rdf_objects.BlobID(b"01234567" * 4)
    blob_data = b"abcdef"

    self.blob_store.WriteBlobs({blob_id: blob_data})

    result = self.blob_store.ReadBlobs([blob_id])
    self.assertEqual(result, {blob_id: blob_data})

  def testMultipleBlobsCanBeWrittenAndThenRead(self):
    blob_ids = [rdf_objects.BlobID((b"%d1234567" % i) * 4) for i in range(10)]
    blob_data = [b"a" * i for i in range(10)]

    self.blob_store.WriteBlobs(dict(zip(blob_ids, blob_data)))

    result = self.blob_store.ReadBlobs(blob_ids)
    self.assertEqual(result, dict(zip(blob_ids, blob_data)))

  def testWriting80MbOfBlobsWithSingleCallWorks(self):
    num_blobs = 80
    blob_ids = [
        rdf_objects.BlobID((b"%02d234567" % i) * 4) for i in range(num_blobs)
    ]
    blob_data = [b"a" * 1024 * 1024] * num_blobs

    self.blob_store.WriteBlobs(dict(zip(blob_ids, blob_data)))

    result = self.blob_store.ReadBlobs(blob_ids)
    self.assertEqual(result, dict(zip(blob_ids, blob_data)))

  def testCheckBlobsExistCorrectlyReportsPresentAndMissingBlobs(self):
    blob_id = rdf_objects.BlobID(b"01234567" * 4)
    blob_data = b"abcdef"

    self.blob_store.WriteBlobs({blob_id: blob_data})

    other_blob_id = rdf_objects.BlobID(b"abcdefgh" * 4)
    result = self.blob_store.CheckBlobsExist([blob_id, other_blob_id])
    self.assertEqual(result, {blob_id: True, other_blob_id: False})
