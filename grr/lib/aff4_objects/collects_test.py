#!/usr/bin/env python
"""Test the various collection objects."""


from grr import config
from grr.lib import aff4
from grr.lib import flags
from grr.lib import test_lib
from grr.lib.aff4_objects import collects
from grr.lib.rdfvalues import flows as rdf_flows
from grr.lib.rdfvalues import paths as rdf_paths
from grr.lib.rdfvalues import protodict as rdf_protodict


class TypedRDFValueCollection(collects.RDFValueCollection):
  _rdf_type = rdf_paths.PathSpec


class TestCollections(test_lib.AFF4ObjectTest):

  def testRDFValueCollections(self):
    urn = "aff4:/test/collection"
    fd = aff4.FACTORY.Create(
        urn, collects.RDFValueCollection, mode="w", token=self.token)

    for i in range(5):
      fd.Add(rdf_flows.GrrMessage(request_id=i))

    fd.Close()

    fd = aff4.FACTORY.Open(urn, token=self.token)
    # Make sure items are stored in order.
    j = 0
    for j, x in enumerate(fd):
      self.assertEqual(j, x.request_id)

    self.assertEqual(j, 4)

    for j in range(len(fd)):
      self.assertEqual(fd[j].request_id, j)

    self.assertIsNone(fd[5])

  def testGRRSignedBlob(self):
    urn = "aff4:/test/collection"

    # The only way to create a GRRSignedBlob is via this constructor.
    fd = collects.GRRSignedBlob.NewFromContent(
        "hello world",
        urn,
        chunk_size=2,
        token=self.token,
        private_key=config.CONFIG["PrivateKeys.executable_signing_private_key"],
        public_key=config.CONFIG["Client.executable_signing_public_key"])

    fd = aff4.FACTORY.Open(urn, token=self.token)

    # Reading works as expected.
    self.assertEqual(fd.read(10000), "hello world")
    self.assertEqual(fd.size, 11)

    # We have 6 collections.
    self.assertEqual(len(fd.collection), 6)

    # Chunking works ok.
    self.assertEqual(fd.collection[0].data, "he")
    self.assertEqual(fd.collection[1].data, "ll")

    # GRRSignedBlob does not support writing.
    self.assertRaises(IOError, fd.write, "foo")

  def testRDFValueCollectionsAppend(self):
    urn = "aff4:/test/collection"
    fd = aff4.FACTORY.Create(
        urn, collects.RDFValueCollection, mode="w", token=self.token)

    for i in range(5):
      fd.Add(rdf_flows.GrrMessage(request_id=i))

    fd.Close()

    fd = aff4.FACTORY.Open(
        urn, collects.RDFValueCollection, mode="rw", token=self.token)

    for i in range(5):
      fd.Add(rdf_flows.GrrMessage(request_id=i + 5))

    fd.Close()

    fd = aff4.FACTORY.Open(urn, token=self.token)
    # Make sure items are stored in order.
    j = 0
    for j, x in enumerate(fd):
      self.assertEqual(j, x.request_id)

    self.assertEqual(j, 9)

  def testChunkSize(self):

    urn = "aff4:/test/chunktest"

    fd = aff4.FACTORY.Create(
        urn, collects.RDFValueCollection, mode="w", token=self.token)
    fd.SetChunksize(1024 * 1024)

    # Estimate the size of the resulting message.
    msg = rdf_flows.GrrMessage(request_id=100)
    msg_size = len(
        rdf_protodict.EmbeddedRDFValue(payload=msg).SerializeToString())
    # Write ~500Kb.
    n = 500 * 1024 / msg_size

    fd.AddAll([rdf_flows.GrrMessage(request_id=i) for i in xrange(n)])

    self.assertEqual(fd.fd.Get(fd.fd.Schema._CHUNKSIZE), 1024 * 1024)
    # There should be 500K of data.
    self.assertGreater(fd.fd.size, 400 * 1024)
    # and there should only be one chunk since 500K is less than the chunk size.
    self.assertEqual(len(fd.fd.chunk_cache._hash), 1)

    fd.Close()

    # Closing the collection empties the chunk_cache.
    self.assertEqual(len(fd.fd.chunk_cache._hash), 0)

    self.assertRaises(ValueError, fd.SetChunksize, (10))

    fd = aff4.FACTORY.Open(
        urn, collects.RDFValueCollection, mode="rw", token=self.token)
    self.assertRaises(ValueError, fd.SetChunksize, (2 * 1024 * 1024))

  def testAddingNoneToUntypedCollectionRaises(self):
    urn = "aff4:/test/collection"
    fd = aff4.FACTORY.Create(
        urn, collects.RDFValueCollection, mode="w", token=self.token)

    self.assertRaises(ValueError, fd.Add, None)
    self.assertRaises(ValueError, fd.AddAll, [None])

  def testAddingNoneViaAddMethodToTypedCollectionWorksCorrectly(self):
    urn = "aff4:/test/collection"
    fd = aff4.FACTORY.Create(
        urn, TypedRDFValueCollection, mode="w", token=self.token)
    # This works, because Add() accepts keyword arguments and builds _rdf_type
    # instance out of them. In the current case there are no keyword arguments
    # specified, so we get default value.
    fd.Add(None)
    fd.Close()

    fd = aff4.FACTORY.Open(urn, token=self.token)
    self.assertEqual(len(fd), 1)
    self.assertEqual(fd[0], rdf_paths.PathSpec())

  def testAddingNoneViaAddAllMethodToTypedCollectionRaises(self):
    urn = "aff4:/test/collection"
    fd = aff4.FACTORY.Create(
        urn, collects.RDFValueCollection, mode="w", token=self.token)

    self.assertRaises(ValueError, fd.AddAll, [None])

  def testSignedBlob(self):
    test_string = "Sample 5"

    urn = "aff4:/test/signedblob"
    collects.GRRSignedBlob.NewFromContent(
        test_string,
        urn,
        private_key=config.CONFIG["PrivateKeys.executable_signing_private_key"],
        public_key=config.CONFIG["Client.executable_signing_public_key"],
        token=self.token)

    sample = aff4.FACTORY.Open(urn, token=self.token)
    self.assertEqual(sample.size, len(test_string))
    self.assertEqual(sample.Tell(), 0)
    self.assertEqual(sample.Read(3), test_string[:3])
    self.assertEqual(sample.Tell(), 3)
    self.assertEqual(sample.Read(30), test_string[3:])
    self.assertEqual(sample.Tell(), len(test_string))
    self.assertEqual(sample.Read(30), "")
    sample.Seek(3)
    self.assertEqual(sample.Tell(), 3)
    self.assertEqual(sample.Read(3), test_string[3:6])


def main(argv):
  # Run the full test suite
  test_lib.GrrTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)
