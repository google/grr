#!/usr/bin/env python
from absl.testing import absltest

from grr_response_server import blob_store as abstract_bs
from grr_response_server.databases import db as abstract_db
from grr_response_server.databases import db_test_utils
from grr_response_server.models import blobs
from grr_response_server.sinks import blob as blob_sink
from grr.test_lib import db_test_lib
from grr_response_proto import rrg_pb2
from grr_response_proto.rrg import blob_pb2 as rrg_blob_pb2


class BlobSinkTest(absltest.TestCase):

  @db_test_lib.WithDatabase
  @db_test_lib.WithDatabaseBlobstore
  def testAccept(self, db: abstract_db.Database, bs: abstract_bs.BlobStore):
    client_id = db_test_utils.InitializeClient(db)

    blob = rrg_blob_pb2.Blob()
    blob.data = b"foo\x00bar\x00baz"

    parcel = rrg_pb2.Parcel()
    parcel.payload.Pack(blob)

    sink = blob_sink.BlobSink()
    sink.Accept(client_id, parcel)

    blob_id = blobs.BlobID.Of(blob.data)
    self.assertEqual(bs.ReadBlob(blob_id), b"foo\x00bar\x00baz")


if __name__ == "__main__":
  absltest.main()
