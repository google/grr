#!/usr/bin/env python
"""Tests for the legacy AFF4-based blob store."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib import flags
from grr_response_server import blob_store_test_mixin
from grr_response_server.blob_stores import memory_stream_bs
from grr.test_lib import test_lib


class MemoryStreamBlobStoreTest(blob_store_test_mixin.BlobStoreTestMixin,
                                test_lib.GRRBaseTest):

  def CreateBlobStore(self):
    return (memory_stream_bs.MemoryStreamBlobStore(), lambda: None)


if __name__ == "__main__":
  flags.StartMain(test_lib.main)
