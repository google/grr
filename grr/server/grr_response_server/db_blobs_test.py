#!/usr/bin/env python
"""Mixin tests for blobs in the relational db."""

from grr_response_server import db
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

  def testWritingBlobReferenceToNonExistentPathRaises(self):
    d = self.db

    path = rdf_objects.ClientPathID(
        client_id="C.bbbbbbbbbbbbbbbb",
        path_type=rdf_objects.PathInfo.PathType.OS,
        path_id=rdf_objects.PathID.FromComponents(["foo", "bar"]))
    blob_ref = rdf_objects.BlobReference(
        offset=0, size=3, blob_id=rdf_objects.BlobID.FromBlobData("foo"))

    with self.assertRaises(db.AtLeastOneUnknownPathError):
      d.WriteClientPathBlobReferences({path: [blob_ref]})

  def testReadingBlobReferenceFromNonExistentPathReturnsEmptyResult(self):
    d = self.db

    path = rdf_objects.ClientPathID(
        client_id="C.bbbbbbbbbbbbbbbb",
        path_type=rdf_objects.PathInfo.PathType.OS,
        path_id=rdf_objects.PathID.FromComponents(["foo", "bar"]))

    res = d.ReadClientPathBlobReferences([path])
    self.assertEqual(res, {path: []})

  def testSingleBlobReferenceCanBeWrittenAndThenRead(self):
    d = self.db

    client_id = self.InitializeClient()
    self.db.WritePathInfos(
        client_id,
        [rdf_objects.PathInfo.OS(components=["foo", "bar"], directory=False)])

    path = rdf_objects.ClientPathID(
        client_id=client_id,
        path_type=rdf_objects.PathInfo.PathType.OS,
        path_id=rdf_objects.PathID.FromComponents(["foo", "bar"]))
    blob_ref = rdf_objects.BlobReference(
        offset=0, size=3, blob_id=rdf_objects.BlobID.FromBlobData("foo"))

    d.WriteClientPathBlobReferences({path: [blob_ref]})

    read_refs = d.ReadClientPathBlobReferences([path])
    self.assertEqual(read_refs, {path: [blob_ref]})

  def testMultipleBlobReferencesCanBeWrittenAndThenRead(self):
    d = self.db

    paths = []
    refs = []

    for i in range(10):
      client_id = self.InitializeClient()
      self.db.WritePathInfos(client_id, [
          rdf_objects.PathInfo.OS(
              components=["foo%d" % i, "bar%d" % i], directory=False)
      ])

      path = rdf_objects.ClientPathID(
          client_id=client_id,
          path_type=rdf_objects.PathInfo.PathType.OS,
          path_id=rdf_objects.PathID.FromComponents(["foo%d" % i,
                                                     "bar%d" % i]))
      blob_ref = rdf_objects.BlobReference(
          offset=0,
          size=i,
          blob_id=rdf_objects.BlobID.FromBlobData("foo%d" % i))

      paths.append(path)
      refs.append([blob_ref])

    d.WriteClientPathBlobReferences(dict(zip(paths, refs)))

    read_refs = d.ReadClientPathBlobReferences(paths)
    self.assertEqual(read_refs, dict(zip(paths, refs)))
