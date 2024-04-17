#!/usr/bin/env python
"""Tests for signed-binary DB functionality."""

from grr_response_proto import objects_pb2
from grr_response_server.databases import db


_test_id1 = objects_pb2.SignedBinaryID(
    binary_type=objects_pb2.SignedBinaryID.BinaryType.EXECUTABLE,
    path="linux/test/hello",
)
_test_id2 = objects_pb2.SignedBinaryID(
    binary_type=objects_pb2.SignedBinaryID.BinaryType.PYTHON_HACK,
    path="windows/test/hello",
)
_test_references1 = objects_pb2.BlobReferences(
    items=[
        objects_pb2.BlobReference(offset=0, size=2, blob_id=b"\xaa" * 32),
        objects_pb2.BlobReference(offset=2, size=3, blob_id=b"\xbb" * 32),
    ]
)
_test_references2 = objects_pb2.BlobReferences(
    items=[
        objects_pb2.BlobReference(offset=0, size=3, blob_id=b"\xcc" * 32),
        objects_pb2.BlobReference(offset=3, size=2, blob_id=b"\xdd" * 32),
    ]
)


class DatabaseTestSignedBinariesMixin(object):
  """Mixin that adds tests for signed binary DB functionality."""

  def testReadSignedBinaryReferences(self):
    self.db.WriteSignedBinaryReferences(_test_id1, _test_references1)
    stored_hash_id, stored_timestamp = self.db.ReadSignedBinaryReferences(
        _test_id1
    )
    self.assertEqual(stored_hash_id, _test_references1)
    self.assertGreater(stored_timestamp.AsMicrosecondsSinceEpoch(), 0)

  def testUpdateSignedBinaryReferences(self):
    self.db.WriteSignedBinaryReferences(_test_id1, _test_references1)
    stored_references1, timestamp1 = self.db.ReadSignedBinaryReferences(
        _test_id1
    )
    self.assertEqual(stored_references1, _test_references1)
    self.db.WriteSignedBinaryReferences(_test_id1, _test_references2)
    stored_references2, timestamp2 = self.db.ReadSignedBinaryReferences(
        _test_id1
    )
    self.assertEqual(stored_references2, _test_references2)
    self.assertGreater(timestamp2, timestamp1)

  def testUnknownSignedBinary(self):
    with self.assertRaises(db.UnknownSignedBinaryError):
      self.db.ReadSignedBinaryReferences(_test_id1)

  def testReadIDsForAllSignedBinaries(self):
    self.db.WriteSignedBinaryReferences(_test_id1, _test_references1)
    self.db.WriteSignedBinaryReferences(_test_id2, _test_references2)
    self.assertCountEqual(
        self.db.ReadIDsForAllSignedBinaries(),
        [
            _test_id1,
            _test_id2,
        ],
    )

  def testDeleteSignedBinaryReferences(self):
    self.db.WriteSignedBinaryReferences(_test_id1, _test_references1)
    self.assertNotEmpty(self.db.ReadIDsForAllSignedBinaries())
    self.db.DeleteSignedBinaryReferences(_test_id1)
    self.assertEmpty(self.db.ReadIDsForAllSignedBinaries())
    # Trying to delete again shouldn't raise.
    self.db.DeleteSignedBinaryReferences(_test_id1)

  def testWriteAndReadLongUnicodePath(self):
    test_id = objects_pb2.SignedBinaryID(
        binary_type=objects_pb2.SignedBinaryID.BinaryType.EXECUTABLE,
        path="linux/" + "🚀" * 1000 + "/hello",
    )

    self.db.WriteSignedBinaryReferences(test_id, _test_references1)
    stored_hash_id, stored_timestamp = self.db.ReadSignedBinaryReferences(
        test_id
    )
    self.assertEqual(stored_hash_id, _test_references1)
    self.assertGreater(stored_timestamp.AsMicrosecondsSinceEpoch(), 0)
    self.assertEqual(
        self.db.ReadIDsForAllSignedBinaries(),
        [test_id],
    )


# This file is a test library and thus does not require a __main__ block.
