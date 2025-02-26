#!/usr/bin/env python
"""Tests for the GCS Blobstore implementation."""

import os
import unittest
import uuid

from absl import app
from google.cloud import storage

from grr_response_server import blob_store_test_mixin
from grr_response_server.blob_stores import gcs_blob_store
from grr_response_server.models import blobs as models_blobs
from grr.test_lib import test_lib


class GCSBlobStoreTest(
    blob_store_test_mixin.BlobStoreTestMixin,
    test_lib.GRRBaseTest,
):

  @classmethod
  def setUpClass(cls):
    super().setUpClass()

    if not os.getenv("STORAGE_EMULATOR_HOST"):
      raise unittest.SkipTest(
          "Storage emulation not found (STORAGE_EMULATOR_HOST is not set)."
      )

    project = "test-project"
    bucket_name = f"test-bucket-{uuid.uuid4()}"

    cls._gcs_bucket = storage.Client(project=project).bucket(bucket_name)
    cls._gcs_config_overrider = test_lib.ConfigOverrider({
        "Blobstore.gcs.project": project,
        "Blobstore.gcs.bucket": bucket_name,
    })
    cls._gcs_config_overrider.Start()

  @classmethod
  def tearDownClass(cls):
    cls._gcs_config_overrider.Stop()
    super().tearDownClass()

  def setUp(self):
    super().setUp()
    self.__class__._gcs_bucket.create()

  def tearDown(self):
    self.__class__._gcs_bucket.delete(force=True)
    super().tearDown()

  def CreateBlobStore(self):
    return (gcs_blob_store.GCSBlobStore(), lambda: None)

  def testEmptyBlobPrefix(self):
    with test_lib.ConfigOverrider({"Blobstore.gcs.blob_prefix": ""}):
      blob_store = gcs_blob_store.GCSBlobStore()
      blob_id = models_blobs.BlobID(b"0123" * 8)
      blob_data = b"abcdefgh"
      blob_store.WriteBlobs({blob_id: blob_data})
      expected_blob_name = bytes(blob_id).hex()
      expected_blob = self.__class__._gcs_bucket.blob(expected_blob_name)
      self.assertTrue(expected_blob.exists())

  def testBlobPrefix(self):
    prefix = str(uuid.uuid4()) + "/"
    with test_lib.ConfigOverrider({"Blobstore.gcs.blob_prefix": prefix}):
      blob_store = gcs_blob_store.GCSBlobStore()
      blob_id = models_blobs.BlobID(b"0123" * 8)
      blob_data = b"abcdefgh"
      blob_store.WriteBlobs({blob_id: blob_data})
      expected_blob_name = f"{prefix}{bytes(blob_id).hex()}"
      expected_blob = self.__class__._gcs_bucket.blob(expected_blob_name)
      self.assertTrue(expected_blob.exists())


if __name__ == "__main__":
  app.run(test_lib.main)
