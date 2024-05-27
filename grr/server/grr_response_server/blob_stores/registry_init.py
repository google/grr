#!/usr/bin/env python
"""Load all blob stores so that they are visible in the registry."""

from grr_response_server import blob_store
from grr_response_server.blob_stores import db_blob_store
from grr_response_server.blob_stores import gcs_blob_store


def RegisterBlobStores():
  """Registers all BlobStore implementations in blob_store.REGISTRY."""
  blob_store.REGISTRY[db_blob_store.DbBlobStore.__name__] = (
      db_blob_store.DbBlobStore
  )
  blob_store.REGISTRY[gcs_blob_store.GCSBlobStore.__name__] = (
      gcs_blob_store.GCSBlobStore
  )
