#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

"""Tests for the flow."""

import itertools
import os
import threading
import time

# pylint: disable=unused-import,g-bad-import-order
# Import this so the aff4 tests will be run.
from grr.lib.aff4_objects import tests
# pylint: enable=unused-import,g-bad-import-order

from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import data_store
from grr.lib import flags
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib import utils
from grr.lib.aff4_objects import aff4_grr
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import crypto as rdf_crypto
from grr.lib.rdfvalues import paths as rdf_paths
from grr.lib.rdfvalues import protodict as rdf_protodict
from grr.server import foreman as rdf_foreman


class ObjectWithLockProtectedAttribute(aff4.AFF4Volume):
  """Test object with a lock-protected attribute."""

  class SchemaCls(aff4.AFF4Object.SchemaCls):
    LOCK_PROTECTED_ATTR = aff4.Attribute("aff4:protected_attr",
                                         rdfvalue.RDFString,
                                         "SomeString",
                                         lock_protected=True)
    UNPROTECTED_ATTR = aff4.Attribute("aff4:unprotected_attr",
                                      rdfvalue.RDFString,
                                      "SomeString",
                                      lock_protected=False)


class DeletionPoolTest(test_lib.GRRBaseTest):
  """Tests for DeletionPool class."""

  def setUp(self):
    super(DeletionPoolTest, self).setUp()
    self.pool = aff4.DeletionPool(token=self.token)

  def _CreateObject(self, urn, aff4_type):
    with aff4.FACTORY.Create(urn, aff4_type, mode="w", token=self.token) as fd:
      return fd

  def testMarkForDeletionAddsObjectsToDeletionSet(self):
    self.pool.MarkForDeletion(rdfvalue.RDFURN("aff4:/a"))
    self.pool.MarkForDeletion(rdfvalue.RDFURN("aff4:/b"))

    self.assertEqual(self.pool.urns_for_deletion,
                     set([rdfvalue.RDFURN("aff4:/a"),
                          rdfvalue.RDFURN("aff4:/b")]))

  def testMarkForDeletionAddsChildrenToDeletionSet(self):
    self._CreateObject("aff4:/a", "AFF4MemoryStream")
    self._CreateObject("aff4:/a/b", "AFF4MemoryStream")

    self.pool.MarkForDeletion(rdfvalue.RDFURN("aff4:/a"))

    self.assertEqual(self.pool.urns_for_deletion,
                     set([rdfvalue.RDFURN("aff4:/a"),
                          rdfvalue.RDFURN("aff4:/a/b")]))

  def testMultiMarkForDeletionAddsMultipleObjectsToDeletionSet(self):
    self.pool.MultiMarkForDeletion([rdfvalue.RDFURN("aff4:/a"),
                                    rdfvalue.RDFURN("aff4:/b")])

    self.assertEqual(self.pool.urns_for_deletion,
                     set([rdfvalue.RDFURN("aff4:/a"),
                          rdfvalue.RDFURN("aff4:/b")]))

  def testMultiMarkForDeletionAddsMultipleObjectsAndChildrenToDeletionSet(self):
    self._CreateObject("aff4:/a", "AFF4MemoryStream")
    self._CreateObject("aff4:/a/b", "AFF4MemoryStream")
    self._CreateObject("aff4:/c", "AFF4MemoryStream")
    self._CreateObject("aff4:/c/d", "AFF4MemoryStream")
    self._CreateObject("aff4:/c/e", "AFF4MemoryStream")

    self.pool.MultiMarkForDeletion([rdfvalue.RDFURN("aff4:/a"),
                                    rdfvalue.RDFURN("aff4:/c")])

    self.assertEqual(self.pool.urns_for_deletion,
                     set([rdfvalue.RDFURN("aff4:/a"),
                          rdfvalue.RDFURN("aff4:/a/b"),
                          rdfvalue.RDFURN("aff4:/c"),
                          rdfvalue.RDFURN("aff4:/c/d"),
                          rdfvalue.RDFURN("aff4:/c/e")]))

  def testReturnsEmptyListOfRootsWhenNoUrnsMarked(self):
    self.assertEqual(self.pool.root_urns_for_deletion, set())

  def testReturnsSingleRootIfTwoUrnsInTheSameSubtreeMarkedForDeletion(self):
    self.pool.MarkForDeletion(rdfvalue.RDFURN("aff4:/a"))
    self.pool.MarkForDeletion(rdfvalue.RDFURN("aff4:/a/b"))

    self.assertEqual(self.pool.root_urns_for_deletion,
                     set([rdfvalue.RDFURN("/a")]))

  def testReturnsTwoRootsIfTwoMarkedUrnsAreFromDifferentSubtrees(self):
    self.pool.MarkForDeletion(rdfvalue.RDFURN("aff4:/a/b"))
    self.pool.MarkForDeletion(rdfvalue.RDFURN("aff4:/b/c"))

    self.assertEqual(self.pool.root_urns_for_deletion,
                     set([rdfvalue.RDFURN("aff4:/a/b"),
                          rdfvalue.RDFURN("aff4:/b/c")]))

  def testReturnsCorrectRootsForShuffledMarkForDeletionCalls(self):
    urns = [
        "aff4:/a/f",
        "aff4:/a/b",
        "aff4:/a/b/c",
        "aff4:/a/b/d",
        "aff4:/a/b/e"]

    for urns_permutation in itertools.permutations(urns):
      pool = aff4.DeletionPool(token=self.token)
      for urn in urns_permutation:
        pool.MarkForDeletion(urn)

      self.assertEqual(
          pool.root_urns_for_deletion,
          set([rdfvalue.RDFURN("aff4:/a/b"),
               rdfvalue.RDFURN("aff4:/a/f")]))

  def testOpenCachesObjectBasedOnUrnAndMode(self):
    self._CreateObject("aff4:/obj", "AFF4MemoryStream")
    obj = self.pool.Open("aff4:/obj")
    self.assertEqual(obj.Get(obj.Schema.TYPE), "AFF4MemoryStream")

    self._CreateObject("aff4:/obj", "AFF4Volume")
    obj = self.pool.Open("aff4:/obj")
    # Check that we still get the old object from the cache.
    self.assertEqual(obj.Get(obj.Schema.TYPE), "AFF4MemoryStream")

    # Check that request with different mode is not cached.
    obj = self.pool.Open("aff4:/obj", mode="rw")
    self.assertEqual(obj.Get(obj.Schema.TYPE), "AFF4Volume")

  def testOpenCachesObjectEvenIfRequestedAff4TypeIsWrong(self):
    self._CreateObject("aff4:/obj", "AFF4MemoryStream")
    self.assertRaises(IOError, self.pool.Open,
                      "aff4:/obj", aff4_type="RDFValueCollection")

    self._CreateObject("aff4:/obj", "AFF4Volume")
    obj = self.pool.Open("aff4:/obj")
    # Check that the original object got cached and we do not make
    # roundtrips to the datastore.
    self.assertEqual(obj.Get(obj.Schema.TYPE), "AFF4MemoryStream")

  def testMultiOpenCachesObjectsBasedOnUrnAndMode(self):
    self._CreateObject("aff4:/obj1", "AFF4MemoryStream")
    self._CreateObject("aff4:/obj2", "AFF4MemoryStream")

    result = self.pool.MultiOpen(["aff4:/obj1", "aff4:/obj2"])
    self.assertEqual(result[0].Get(result[0].Schema.TYPE), "AFF4MemoryStream")
    self.assertEqual(result[1].Get(result[1].Schema.TYPE), "AFF4MemoryStream")

    self._CreateObject("aff4:/obj1", "AFF4Volume")
    self._CreateObject("aff4:/obj2", "AFF4Volume")

    # Check that this result is still cached.
    result = self.pool.MultiOpen(["aff4:/obj1", "aff4:/obj2"])
    self.assertEqual(result[0].Get(result[0].Schema.TYPE), "AFF4MemoryStream")
    self.assertEqual(result[1].Get(result[1].Schema.TYPE), "AFF4MemoryStream")

    # Check that request with different mode is not cached.
    result = self.pool.MultiOpen(["aff4:/obj1", "aff4:/obj2"], mode="rw")
    self.assertEqual(result[0].Get(result[0].Schema.TYPE), "AFF4Volume")
    self.assertEqual(result[1].Get(result[1].Schema.TYPE), "AFF4Volume")

  def testMultiOpenCachesObjectsEvenIfRequestedAff4TypeIsWrong(self):
    self._CreateObject("aff4:/obj1", "AFF4MemoryStream")
    self._CreateObject("aff4:/obj2", "AFF4MemoryStream")

    result = self.pool.MultiOpen(["aff4:/obj1", "aff4:/obj2"],
                                 aff4_type="RDFValueCollection")
    self.assertFalse(result)

    self._CreateObject("aff4:/obj1", "AFF4Volume")
    self._CreateObject("aff4:/obj2", "AFF4Volume")

    # Check that original objects got cached despite the fact that they didn't
    # match the aff4_type in the original pool request.
    result = self.pool.MultiOpen(["aff4:/obj1", "aff4:/obj2"])
    self.assertEqual(result[0].Get(result[0].Schema.TYPE), "AFF4MemoryStream")
    self.assertEqual(result[1].Get(result[1].Schema.TYPE), "AFF4MemoryStream")

  def testMultiOpenQueriesOnlyNonCachedObjects(self):
    self._CreateObject("aff4:/obj1", "AFF4MemoryStream")
    self._CreateObject("aff4:/obj2", "AFF4MemoryStream")

    result = self.pool.MultiOpen(["aff4:/obj1"])
    self.assertEqual(len(result), 1)
    self.assertEqual(result[0].Get(result[0].Schema.TYPE), "AFF4MemoryStream")

    self._CreateObject("aff4:/obj1", "AFF4Volume")
    self._CreateObject("aff4:/obj2", "AFF4Volume")

    result = dict((obj.urn.Basename(), obj) for obj in
                  self.pool.MultiOpen(["aff4:/obj1", "aff4:/obj2"]))
    # Check that only previously uncached objects got fetched. Cached objects
    # were left intact.
    self.assertEqual(result["obj1"].Get(result["obj1"].Schema.TYPE),
                     "AFF4MemoryStream")
    self.assertEqual(result["obj2"].Get(result["obj2"].Schema.TYPE),
                     "AFF4Volume")

  def testMultiOpenDoesNotCacheNegativeResults(self):
    result = self.pool.MultiOpen([""])
    self.assertFalse(result)

    self._CreateObject("aff4:/obj1", "AFF4MemoryStream")
    result = self.pool.MultiOpen(["aff4:/obj1"])
    self.assertEqual(result[0].Get(result[0].Schema.TYPE), "AFF4MemoryStream")

  def testListChildrenResultsAreCached(self):
    self._CreateObject("aff4:/a", "AFF4Volume")
    self._CreateObject("aff4:/a/b", "AFF4Volume")

    result = self.pool.ListChildren("aff4:/a")
    self.assertListEqual(result, ["aff4:/a/b"])

    self._CreateObject("aff4:/a/c", "AFF4Volume")
    result = self.pool.ListChildren("aff4:/a")
    # Check that the result was cached and newly created item is not reflected
    # in the request.
    self.assertListEqual(result, ["aff4:/a/b"])

  def testMultiListChildrenResultsAreCached(self):
    result = self.pool.MultiListChildren(["aff4:/a", "aff4:/b"])
    self.assertEqual(result, {"aff4:/a": [], "aff4:/b": []})

    self._CreateObject("aff4:/a", "AFF4Volume")
    self._CreateObject("aff4:/a/b", "AFF4Volume")

    result = self.pool.MultiListChildren(["aff4:/a", "aff4:/b"])
    self.assertEqual(result, {"aff4:/a": [], "aff4:/b": []})

  def testMultiListeChildreQueriesOnlyNonCachedUrns(self):
    self._CreateObject("aff4:/a", "AFF4Volume")
    self._CreateObject("aff4:/a/b", "AFF4Volume")

    self._CreateObject("aff4:/b", "AFF4Volume")
    self._CreateObject("aff4:/b/c", "AFF4Volume")

    result = self.pool.MultiListChildren(["aff4:/a"])
    self.assertEqual(result, {"aff4:/a": ["aff4:/a/b"]})

    self._CreateObject("aff4:/a/foo", "AFF4Volume")
    self._CreateObject("aff4:/b/bar", "AFF4Volume")

    # Check that cached children lists are not refetched.
    result = self.pool.MultiListChildren(["aff4:/a", "aff4:/b"])
    self.assertEqual(result, {"aff4:/a": ["aff4:/a/b"],
                              "aff4:/b": ["aff4:/b/bar", "aff4:/b/c"]})

  def testRecursiveMultiListChildrenResultsAreCached(self):
    result = self.pool.RecursiveMultiListChildren(["aff4:/a", "aff4:/b"])
    self.assertEqual(result, {"aff4:/a": [], "aff4:/b": []})

    self._CreateObject("aff4:/a", "AFF4Volume")
    self._CreateObject("aff4:/a/b", "AFF4Volume")

    result = self.pool.MultiListChildren(["aff4:/a", "aff4:/b"])
    self.assertEqual(result, {"aff4:/a": [], "aff4:/b": []})

  def testRecursiveMultiListChildrenQueriesOnlyNonCachedUrns(self):
    self._CreateObject("aff4:/a", "AFF4Volume")
    self._CreateObject("aff4:/a/b", "AFF4Volume")
    self._CreateObject("aff4:/a/b/c", "AFF4Volume")

    # This should put aff4:/a and aff4:/a/b into the cache.
    # Note that there's aff4:/a/b/c children were not queried and cached.
    self.pool.MultiListChildren(["aff4:/a", "aff4:/a/b"])

    self._CreateObject("aff4:/a/foo", "AFF4Volume")
    self._CreateObject("aff4:/a/b/c/d", "AFF4Volume")

    # aff4:/a children were cached, so aff4:/a/foo won't be present in
    # the results. On the other hand, aff4:/a/b/c/d should be in the
    # results because children of aff4:/a/b/c weren't queried and cached.
    result = self.pool.RecursiveMultiListChildren(["aff4:/a"])

    self.assertEqual(result, {"aff4:/a": ["aff4:/a/b"],
                              "aff4:/a/b": ["aff4:/a/b/c"],
                              "aff4:/a/b/c": ["aff4:/a/b/c/d"],
                              "aff4:/a/b/c/d": []})


class AFF4Tests(test_lib.AFF4ObjectTest):
  """Test the AFF4 abstraction."""

  def testNonVersionedAttribute(self):
    """Test that non versioned attributes work."""
    client = aff4.FACTORY.Create(self.client_id, "VFSGRRClient", mode="w",
                                 token=self.token)

    # We update the client hostname twice - Since hostname is versioned we
    # expect two versions of this object.
    client.Set(client.Schema.HOSTNAME("client1"))
    client.Flush()

    client.Set(client.Schema.HOSTNAME("client1"))
    client.Flush()

    client_fd = aff4.FACTORY.Open(self.client_id, age=aff4.ALL_TIMES,
                                  token=self.token)

    # Versions are represented by the TYPE attribute.
    versions = list(client_fd.GetValuesForAttribute(client_fd.Schema.TYPE))
    self.assertEqual(len(versions), 2)

    # Now update the CLOCK attribute twice. Since CLOCK is not versioned, this
    # should not add newer versions to this object.
    client.Set(client.Schema.CLOCK())
    client.Flush()

    client.Set(client.Schema.CLOCK())
    client.Flush()

    client_fd = aff4.FACTORY.Open(self.client_id, age=aff4.ALL_TIMES,
                                  token=self.token)

    # Versions are represented by the TYPE attribute.
    new_versions = list(client_fd.GetValuesForAttribute(client_fd.Schema.TYPE))

    self.assertEqual(versions, new_versions)

    # There should also only be one clock attribute
    clocks = list(client_fd.GetValuesForAttribute(client_fd.Schema.CLOCK))
    self.assertEqual(len(clocks), 1)
    self.assertEqual(clocks[0].age, 0)

    fd = aff4.FACTORY.Create("aff4:/foobar", "AFF4Image", token=self.token)
    fd.Set(fd.Schema._CHUNKSIZE(1))
    fd.Set(fd.Schema._CHUNKSIZE(200))
    fd.Set(fd.Schema._CHUNKSIZE(30))

    fd.Flush()

    fd = aff4.FACTORY.Open("aff4:/foobar", mode="rw", token=self.token)
    self.assertEqual(fd.Get(fd.Schema._CHUNKSIZE), 30)

  def testGetVersions(self):
    """Test we can retrieve versions."""
    client = aff4.FACTORY.Create(self.client_id, "VFSGRRClient", mode="w",
                                 token=self.token)
    # Update the hostname twice, expect two versions of this object.
    client.Set(client.Schema.HOSTNAME("client1"))
    client.Flush()
    client.Set(client.Schema.HOSTNAME("client2"))
    client.Flush()

    # Now create as a different type.
    vfsfile = aff4.FACTORY.Create(self.client_id, "VFSFile", mode="w",
                                  token=self.token)
    vfsfile.Flush()

    ver_list = list(aff4.FACTORY.OpenDiscreteVersions(self.client_id,
                                                      token=self.token))
    self.assertEqual(len(ver_list), 3)
    v1, v2, v3 = ver_list

    self.assertTrue(isinstance(v1, aff4_grr.VFSFile))
    self.assertTrue(isinstance(v3, aff4_grr.VFSGRRClient))
    self.assertTrue(int(v1.Get(v1.Schema.TYPE).age) >
                    int(v2.Get(v2.Schema.TYPE).age))
    self.assertEqual(v2.Get(v2.Schema.TYPE), "VFSGRRClient")
    self.assertEqual(str(v2.Get(v2.Schema.HOSTNAME)), "client2")

  def _CheckAFF4AttributeDefaults(self, client):
    self.assertEqual(client.Get(client.Schema.HOSTNAME), "client1")
    self.assertEqual(client.Get(client.Schema.DOESNOTEXIST, "mydefault"),
                     "mydefault")
    self.assertEqual(client.Get(client.Schema.DOESNOTEXIST,
                                default="mydefault"), "mydefault")
    self.assertEqual(client.Get(client.Schema.DOESNOTEXIST,
                                None), None)
    self.assertEqual(client.Get(client.Schema.DOESNOTEXIST,
                                default=None), None)

  def testGetBadAttribute(self):
    """Test checking of non-existent attributes."""
    # Check behaviour when we specify a type
    client = aff4.FACTORY.Create(self.client_id, "VFSGRRClient", mode="w",
                                 token=self.token)
    client.Set(client.Schema.HOSTNAME("client1"))
    client.Flush()

    self.assertEqual(client.Get(client.Schema.HOSTNAME), "client1")

    # This should raise since we specified a aff4_type in Create
    self.assertRaises(aff4.BadGetAttributeError, getattr, client.Schema,
                      "DOESNOTEXIST")

    # Check we get the same result from the existing object code path in create
    client = aff4.FACTORY.Create(self.client_id, "VFSGRRClient", mode="rw",
                                 token=self.token)

    self.assertEqual(client.Get(client.Schema.HOSTNAME), "client1")
    self.assertRaises(aff4.BadGetAttributeError, getattr, client.Schema,
                      "DOESNOTEXIST")

    # Check we get the same result from Open
    client = aff4.FACTORY.Open(self.client_id, "VFSGRRClient", mode="rw",
                               token=self.token)

    self.assertEqual(client.Get(client.Schema.HOSTNAME), "client1")
    self.assertRaises(aff4.BadGetAttributeError, getattr, client.Schema,
                      "DOESNOTEXIST")

    # Check we get the same result from MultiOpen
    clients = aff4.FACTORY.MultiOpen([self.client_id], aff4_type="VFSGRRClient",
                                     mode="rw", token=self.token)
    for client in clients:
      self.assertEqual(client.Get(client.Schema.HOSTNAME), "client1")
      self.assertRaises(aff4.BadGetAttributeError, getattr, client.Schema,
                        "DOESNOTEXIST")

    # Make sure we don't raise if no type specified. No need to check create,
    # since a type must always be specified.
    client = aff4.FACTORY.Open(self.client_id, mode="rw",
                               token=self.token)
    self.assertEqual(client.Get(client.Schema.HOSTNAME), "client1")
    self.assertEqual(client.Get(client.Schema.DOESNOTEXIST), None)

    # Check we get the same result from MultiOpen
    clients = aff4.FACTORY.MultiOpen([self.client_id], mode="rw",
                                     token=self.token)
    for client in clients:
      self.assertEqual(client.Get(client.Schema.HOSTNAME), "client1")
      self.assertEqual(client.Get(client.Schema.DOESNOTEXIST), None)

  def testAppendAttribute(self):
    """Test that append attribute works."""
    # Create an object to carry attributes
    obj = aff4.FACTORY.Create("foobar", "AFF4Object", token=self.token)
    obj.Set(obj.Schema.STORED("www.google.com"))
    obj.Close()

    obj = aff4.FACTORY.Open("foobar", mode="rw", token=self.token,
                            age=aff4.ALL_TIMES)
    self.assertEqual(1, len(list(obj.GetValuesForAttribute(obj.Schema.STORED))))

    # Add a bunch of attributes now.
    for i in range(5):
      obj.AddAttribute(obj.Schema.STORED("example.com/%s" % i))

    # There should be 6 there now
    self.assertEqual(6, len(list(obj.GetValuesForAttribute(obj.Schema.STORED))))
    obj.Close()

    # Check that when read back from the data_store we stored them all
    obj = aff4.FACTORY.Open("foobar", token=self.token, age=aff4.ALL_TIMES)
    self.assertEqual(6, len(list(obj.GetValuesForAttribute(obj.Schema.STORED))))

  def testLastAddedAttributeWinsWhenTimestampsAreEqual(self):
    with test_lib.FakeTime(42):
      with aff4.FACTORY.Create("foobar", "AFF4Object", token=self.token) as obj:
        obj.Set(obj.Schema.STORED("foo"))
        obj.Set(obj.Schema.STORED("bar"))

    obj = aff4.FACTORY.Open("foobar", token=self.token)
    self.assertEqual(obj.Get(obj.Schema.STORED), "bar")

  def testFlushNewestTime(self):
    """Flush with age policy NEWEST_TIME should only keeps a single version."""
    # Create an object to carry attributes
    obj = aff4.FACTORY.Create("foobar", "AFF4Object", token=self.token)
    obj.Set(obj.Schema.STORED("www.google.com"))
    obj.Close()

    obj = aff4.FACTORY.Open("foobar", mode="rw", token=self.token,
                            age=aff4.NEWEST_TIME)

    self.assertEqual(1, len(obj.synced_attributes[obj.Schema.STORED.predicate]))

    # Add a bunch of attributes now.
    for i in range(5):
      obj.AddAttribute(obj.Schema.STORED("example.com/%s" % i))

    # There should be 5 unsynced versions now
    self.assertEqual(5, len(obj.new_attributes[obj.Schema.STORED.predicate]))
    obj.Flush()

    # When we sync there should be no more unsynced attributes.
    self.assertEqual({}, obj.new_attributes)

    # But there should only be a single synced attribute since this object has a
    # NEWEST_TIME age policy.
    self.assertEqual(1, len(obj.synced_attributes[obj.Schema.STORED.predicate]))

    # The latest version should be kept.
    self.assertEqual(obj.Get(obj.Schema.STORED), "example.com/4")

  def testCopyAttributes(self):
    # Create an object to carry attributes
    obj = aff4.FACTORY.Create("foobar", "AFF4Object", token=self.token)
    # Add a bunch of attributes now.
    for i in range(5):
      obj.AddAttribute(obj.Schema.STORED("example.com/%s" % i))
    obj.Close()

    obj = aff4.FACTORY.Open("foobar", mode="r", token=self.token,
                            age=aff4.ALL_TIMES)
    # There should be 5 attributes now
    self.assertEqual(5, len(list(obj.GetValuesForAttribute(obj.Schema.STORED))))

    new_obj = aff4.FACTORY.Create("new_foobar", "AFF4Object", token=self.token)
    new_obj.Copy(new_obj.Schema.STORED, obj, obj.Schema.STORED)
    new_obj.Close()

    new_obj = aff4.FACTORY.Open("new_foobar", mode="r", token=self.token,
                                age=aff4.ALL_TIMES)
    # Check that attribute got copied properly
    self.assertListEqual(list(obj.GetValuesForAttribute(obj.Schema.STORED)),
                         list(new_obj.GetValuesForAttribute(obj.Schema.STORED)))

  def testAttributeSet(self):
    obj = aff4.FACTORY.Create("foobar", "AFF4Object", token=self.token)
    self.assertFalse(obj.IsAttributeSet(obj.Schema.STORED))
    obj.Set(obj.Schema.STORED("www.google.com"))
    self.assertTrue(obj.IsAttributeSet(obj.Schema.STORED))
    obj.Close()

    obj = aff4.FACTORY.Open("foobar", token=self.token)
    self.assertTrue(obj.IsAttributeSet(obj.Schema.STORED))

  def testCreateObject(self):
    """Test that we can create a new object."""
    path = "/C.0123456789abcdef/foo/bar/hello.txt"

    fd = aff4.FACTORY.Create(path, "AFF4MemoryStream", token=self.token)
    fd.Flush()

    # Now object is ready for use
    fd.Write("hello")
    fd.Close()

    fd = aff4.FACTORY.Open(path, token=self.token)
    self.assertEqual(fd.Read(100), "hello")

    # Make sure that we have intermediate objects created.
    for path in ["aff4:/C.0123456789abcdef", "aff4:/C.0123456789abcdef/foo",
                 "aff4:/C.0123456789abcdef/foo/bar",
                 "aff4:/C.0123456789abcdef/foo/bar/hello.txt"]:
      fd = aff4.FACTORY.Open(path, token=self.token)
      last = fd.Get(fd.Schema.LAST)
      self.assertGreater(int(last), 1330354592221974)

  def testCreateWithPool(self):
    """Tests that we can create aff4 objects using a pool."""
    path1 = "aff4:/test/pool_memory_stream"
    path2 = "aff4:/test/pool_memory_stream2"

    pool = data_store.DB.GetMutationPool(token=self.token)

    for path in [path1, path2]:
      fd = aff4.FACTORY.Create(
          path, "AFF4UnversionedMemoryStream",
          mode="w", mutation_pool=pool, token=self.token)
      content = "TestData" * 10
      fd.Write(content)
      fd.Close()

    # Make sure nothing has been written to the paths we use.
    for path in [path1, path2]:
      for subject in data_store.DB.subjects:
        self.assertNotIn(path, subject)

    pool.Flush()

    for path in [path1, path2]:
      for subject in data_store.DB.subjects:
        if path in subject:
          break
      else:
        self.fail("Nothing was written to the test path (%s)" % path)

    fd = aff4.FACTORY.Open(path1, token=self.token)
    self.assertEqual(fd.read(100), content)

  def testObjectUpgrade(self):
    """Test that we can create a new object of a different type."""
    path = "C.0123456789abcdef"

    # Write the first object
    with aff4.FACTORY.Create(path, "VFSGRRClient", token=self.token) as fd:
      fd.Set(fd.Schema.HOSTNAME("blah"))
      original_fd = fd

    # Check it got created
    with aff4.FACTORY.Open(path, "VFSGRRClient", token=self.token) as fd:
      self.assertEqual(fd.Get(fd.Schema.HOSTNAME), "blah")
      self.assertEqual(fd.Get(fd.Schema.TYPE), "VFSGRRClient")

    # Overwrite with a new object of different type
    with aff4.FACTORY.Create(path, "AFF4MemoryStream",
                             token=self.token) as fd:
      fd.Write("hello")

    # Check that the object is now an AFF4MemoryStream
    with aff4.FACTORY.Open(path, "AFF4MemoryStream", token=self.token) as fd:
      self.assertEqual(fd.Read(100), "hello")
      self.assertEqual(fd.Get(fd.Schema.TYPE), "AFF4MemoryStream")
      self.assertRaises(aff4.BadGetAttributeError, getattr, fd.Schema,
                        "HOSTNAME")

    # Attributes of previous objects are actually still accessible. Some code
    # relies on this behaviour so we verify it here.
    with aff4.FACTORY.Open(path, token=self.token) as fd:
      self.assertEqual(fd.Read(100), "hello")
      self.assertEqual(fd.Get(original_fd.Schema.HOSTNAME), "blah")

  def testDelete(self):
    """Check that deleting the object works."""
    path = "/C.0123456789abcdef/foo/bar/hello.txt"

    fd = aff4.FACTORY.Create(path, "AFF4MemoryStream", token=self.token)
    fd.Write("hello")
    fd.Close()

    # Delete the directory and check that the file in it is also removed.
    aff4.FACTORY.Delete(os.path.dirname(path), token=self.token)
    self.assertRaises(IOError, aff4.FACTORY.Open, path, "AFF4MemoryStream",
                      token=self.token)

  def testDeleteRaisesWhenTryingToDeleteRoot(self):
    self.assertRaises(RuntimeError, aff4.FACTORY.Delete, "aff4:/",
                      token=self.token)

  def testRecursiveDelete(self):
    """Checks that recusrive deletion of objects works."""

    paths_to_delete = ["aff4:/tmp/dir1/hello1.txt",
                       "aff4:/tmp/dir1/foo/hello2.txt",
                       "aff4:/tmp/dir1/foo/bar/hello3.txt"]
    safe_paths = ["aff4:/tmp/dir2/hello4.txt"]

    for path in paths_to_delete + safe_paths:
      with aff4.FACTORY.Create(path, "AFF4MemoryStream",
                               token=self.token) as fd:
        fd.Write("hello")

    fd = aff4.FACTORY.Open("aff4:/tmp", token=self.token)
    self.assertListEqual(sorted(fd.ListChildren()),
                         ["aff4:/tmp/dir1", "aff4:/tmp/dir2"])

    aff4.FACTORY.Delete("aff4:/tmp/dir1", token=self.token)
    for path in paths_to_delete:
      self.assertRaises(IOError, aff4.FACTORY.Open, path, "AFF4MemoryStream",
                        token=self.token)

      fd = aff4.FACTORY.Open(os.path.dirname(path), token=self.token)
      self.assertFalse(list(fd.ListChildren()))

    fd = aff4.FACTORY.Open("aff4:/tmp", token=self.token)
    self.assertListEqual(list(fd.ListChildren()),
                         ["aff4:/tmp/dir2"])

    fd = aff4.FACTORY.Open("aff4:/tmp/dir2", token=self.token)
    self.assertListEqual(list(fd.ListChildren()),
                         ["aff4:/tmp/dir2/hello4.txt"])

  def testMultiDeleteRaisesWhenTryingToDeleteRoot(self):
    self.assertRaises(RuntimeError, aff4.FACTORY.MultiDelete,
                      ["aff4:/a", "aff4:/"], token=self.token)

  def testMultiDeleteRemovesAllTracesOfObjectsFromDataStore(self):
    unique_token = "recursive_delete"

    for i in range(5):
      for j in range(5):
        with aff4.FACTORY.Create(
            "aff4:" + ("/%s%d" % (unique_token, i)) * (j + 1),
            "AFF4Volume", token=self.token):
          pass

    aff4.FACTORY.MultiDelete(
        ["aff4:/%s%d" % (unique_token, i) for i in range(5)],
        token=self.token)

    # NOTE: We assume that tests are running with FakeDataStore.
    for subject, subject_data in data_store.DB.subjects.items():
      self.assertFalse(unique_token in subject)

      for column_name, values in subject_data.items():
        self.assertFalse(unique_token in column_name)

        for value, _ in values:
          self.assertFalse(unique_token in utils.SmartUnicode(value))

  def testClientObject(self):
    fd = aff4.FACTORY.Create(self.client_id, "VFSGRRClient", token=self.token)

    # Certs invalid - The RDFX509Cert should check the validity of the cert
    self.assertRaises(rdfvalue.DecodeError, rdf_crypto.RDFX509Cert, "My cert")

    fd.Close()

  def testAFF4MemoryStream(self):
    """Tests the AFF4MemoryStream."""

    path = "/C.12345/memorystreamtest"

    fd = aff4.FACTORY.Create(path, "AFF4MemoryStream", token=self.token)
    self.assertEqual(fd.size, 0)
    self.assertEqual(fd.Tell(), 0)

    size = 0
    for i in range(100):
      data = "Test%08X\n" % i
      fd.Write(data)
      size += len(data)
      self.assertEqual(fd.size, size)
      self.assertEqual(fd.Tell(), size)
    fd.Close()

    fd = aff4.FACTORY.Open(path, mode="rw", token=self.token)
    self.assertEqual(fd.size, size)
    self.assertEqual(fd.Tell(), 0)
    fd.Seek(size)
    self.assertEqual(fd.Tell(), size)
    fd.Seek(100)
    fd.Write("Hello World!")
    self.assertEqual(fd.size, size)
    fd.Close()

    fd = aff4.FACTORY.Open(path, mode="rw", token=self.token)
    self.assertEqual(fd.size, size)
    data = fd.Read(size)
    self.assertEqual(len(data), size)
    self.assertTrue("Hello World!" in data)
    fd.Close()

  def ExerciseAFF4ImageBase(self, classname):
    """Run basic tests on a subclass of AFF4ImageBase."""
    path = "/C.12345/aff4image"

    with aff4.FACTORY.Create(path, classname, token=self.token) as fd:
      fd.SetChunksize(10)

      # Make lots of small writes - The length of this string and the chunk size
      # are relative primes for worst case.
      for i in range(10):
        fd.Write("Test%08X\n" % i)

    with aff4.FACTORY.Open(path, token=self.token) as fd:
      for i in range(10):
        self.assertEqual(fd.Read(13), "Test%08X\n" % i)

    with aff4.FACTORY.Create(path, classname, mode="rw",
                             token=self.token) as fd:
      fd.Set(fd.Schema._CHUNKSIZE(10))

      # Overflow the cache (Cache is 100 chunks, can hold 10*100 bytes).
      fd.Write("X" * 1100)
      self.assertEqual(fd.size, 1100)
      # Now rewind a bit and write something.
      fd.seek(fd.size - 100)
      fd.Write("Hello World")
      self.assertEqual(fd.size, 1100)
      # Now append to the end.
      fd.seek(fd.size)
      fd.Write("Y" * 10)
      self.assertEqual(fd.size, 1110)
      # And verify everything worked as expected.
      fd.seek(997)
      data = fd.Read(17)
      self.assertEqual("XXXHello WorldXXX", data)

      fd.seek(1097)
      data = fd.Read(6)
      self.assertEqual("XXXYYY", data)

    # Set the max_unbound_read_size to last size of object at path
    # before object creation for unbound read() tests.
    with test_lib.ConfigOverrider({
        "Server.max_unbound_read_size": 1110}):

      with aff4.FACTORY.Create(path, classname, mode="rw",
                               token=self.token) as fd:
        fd.Set(fd.Schema._CHUNKSIZE(10))
        # Verify the unbound read returns 110 bytes
        data = fd.read()
        self.assertEqual(len(data), 1110)
        # Append additional data and retry as oversized unbound read
        fd.seek(fd.size)
        fd.Write("X" * 10)
        fd.seek(0)
        self.assertRaises(aff4.OversizedRead, fd.read)

  def testAFF4Image(self):
    self.ExerciseAFF4ImageBase("AFF4Image")

  def testAFF4UnversionedImage(self):
    self.ExerciseAFF4ImageBase("AFF4UnversionedImage")

  def testAFF4ImageSize(self):
    path = "/C.12345/aff4imagesize"

    fd = aff4.FACTORY.Create(path, "AFF4Image", token=self.token)
    fd.SetChunksize(10)

    size = 0
    for i in range(99):
      data = "Test%08X\n" % i
      fd.Write(data)
      size += len(data)
      self.assertEqual(fd.size, size)

    fd.Close()

    # Check that size is preserved.
    fd = aff4.FACTORY.Open(path, mode="rw", token=self.token)
    self.assertEqual(fd.size, size)

    # Now append some more data.
    fd.seek(fd.size)
    for i in range(99):
      data = "Test%08X\n" % i
      fd.Write(data)
      size += len(data)
      self.assertEqual(fd.size, size)

    fd.Close()

    # Check that size is preserved.
    fd = aff4.FACTORY.Open(path, mode="rw", token=self.token)
    self.assertEqual(fd.size, size)
    fd.Close()

    # Writes in the middle should not change size.
    fd = aff4.FACTORY.Open(path, mode="rw", token=self.token)
    fd.Seek(100)
    fd.Write("Hello World!")
    self.assertEqual(fd.size, size)
    fd.Close()

    # Check that size is preserved.
    fd = aff4.FACTORY.Open(path, mode="rw", token=self.token)
    self.assertEqual(fd.size, size)
    data = fd.Read(fd.size)
    self.assertEqual(len(data), size)
    self.assertTrue("Hello World" in data)
    fd.Close()

  def testAFF4ImageWithFlush(self):
    """Make sure the AFF4Image can survive with partial flushes."""
    path = "/C.12345/foo"

    self.WriteImage(path, "Test")

    fd = aff4.FACTORY.Open(path, token=self.token)
    for i in range(100):
      self.assertEqual(fd.Read(13), "Test%08X\n" % i)

  def WriteImage(self, path, prefix="Test", timestamp=0, classname="AFF4Image"):
    with utils.Stubber(time, "time", lambda: timestamp):
      fd = aff4.FACTORY.Create(path, classname, mode="w", token=self.token)

      timestamp += 1
      fd.SetChunksize(10)

      # Make lots of small writes - The length of this string and the chunk size
      # are relative primes for worst case.
      for i in range(100):
        fd.Write("%s%08X\n" % (prefix, i))

        # Flush after every write.
        fd.Flush()

        # And advance the time.
        timestamp += 1

      fd.Close()

  def testAFF4ImageWithVersioning(self):
    """Make sure the AFF4Image can do multiple versions."""
    path = "/C.12345/foowithtime"

    self.WriteImage(path, "Time1", timestamp=1000)

    # Write a newer version.
    self.WriteImage(path, "Time2", timestamp=2000)

    fd = aff4.FACTORY.Open(path, token=self.token, age=(0, 1150 * 1e6))

    for i in range(100):
      s = "Time1%08X\n" % i
      self.assertEqual(fd.Read(len(s)), s)

    fd = aff4.FACTORY.Open(path, token=self.token, age=(0, 2250 * 1e6))
    for i in range(100):
      s = "Time2%08X\n" % i
      self.assertEqual(fd.Read(len(s)), s)

  def testAFF4ImageWithoutVersioning(self):
    """Make sure the AFF4UnversionedImage does not do multiple versions."""
    path = "/C.12345/foowithtime"

    self.WriteImage(path, "Time1", timestamp=1000,
                    classname="AFF4UnversionedImage")

    # Write a newer version.
    self.WriteImage(path, "Time2", timestamp=2000,
                    classname="AFF4UnversionedImage")

    fd = aff4.FACTORY.Open(path, token=self.token, age=(0, 1150 * 1e6))

    for i in range(100):
      s = "Time2%08X\n" % i
      self.assertEqual(fd.Read(len(s)), s)

    fd = aff4.FACTORY.Open(path, token=self.token, age=(0, 2250 * 1e6))
    for i in range(100):
      s = "Time2%08X\n" % i
      self.assertEqual(fd.Read(len(s)), s)

  def testAFF4ImageContentLastUpdated(self):
    """Make sure CONTENT_LAST gets updated only when content is written."""
    path = "/C.12345/contentlastchecker"

    self.WriteImage(path, timestamp=1)

    fd = aff4.FACTORY.Open(path, token=self.token)
    # Make sure the attribute was written when the write occured.
    self.assertEqual(int(fd.GetContentAge()), 101000000)

    # Write the image again, later in time.
    self.WriteImage(path, timestamp=2)

    fd = aff4.FACTORY.Open(path, token=self.token)
    self.assertEqual(int(fd.GetContentAge()), 102000000)

  def testAFF4FlowObject(self):
    """Test the AFF4 Flow object."""
    client = aff4.FACTORY.Create(self.client_id, "VFSGRRClient",
                                 token=self.token)
    client.Close()

    # Start some new flows on it
    session_ids = []
    for _ in range(10):
      session_ids.append(
          flow.GRRFlow.StartFlow(client_id=self.client_id,
                                 flow_name="FlowOrderTest", token=self.token))

    # Try to open a single flow.
    flow_obj = aff4.FACTORY.Open(session_ids[0], mode="r", token=self.token)

    self.assertEqual(flow_obj.state.context.args.flow_name, "FlowOrderTest")
    self.assertEqual(flow_obj.session_id, session_ids[0])

    self.assertEqual(flow_obj.__class__.__name__, "FlowOrderTest")

  def testQuery(self):
    """Test the AFF4Collection object."""
    # First we create a fixture
    client_id = "C.%016X" % 0
    test_lib.ClientFixture(client_id, token=self.token)

    fd = aff4.FACTORY.Open(rdf_client.ClientURN(client_id).Add(
        "/fs/os/c"), token=self.token)

    # Test that we can match a unicode char.
    matched = list(fd.Query(u"subject matches '中'"))
    self.assertEqual(len(matched), 1)
    self.assertEqual(utils.SmartUnicode(matched[0].urn),
                     u"aff4:/C.0000000000000000/"
                     u"fs/os/c/中国新闻网新闻中")

    # Test that we can match special chars.
    matched = list(fd.Query(ur"subject matches '\]\['"))
    self.assertEqual(len(matched), 1)
    self.assertEqual(utils.SmartUnicode(matched[0].urn),
                     u"aff4:/C.0000000000000000/"
                     u"fs/os/c/regex.*?][{}--")

    # Test the OpenChildren function on files that contain regex chars.
    fd = aff4.FACTORY.Open(rdf_client.ClientURN(client_id).Add(
        r"/fs/os/c/regex\V.*?]xx[{}--"), token=self.token)

    children = list(fd.OpenChildren())
    self.assertEqual(len(children), 1)
    self.assertTrue("regexchild" in utils.SmartUnicode(children[0].urn))

    # Test that OpenChildren works correctly on Unicode names.
    fd = aff4.FACTORY.Open(rdf_client.ClientURN(client_id).Add(
        "/fs/os/c"), token=self.token)

    children = list(fd.OpenChildren())
    # All children must have a valid type.
    for child in children:
      self.assertNotEqual(child.Get(child.Schema.TYPE), "VFSVolume")

    urns = [utils.SmartUnicode(x.urn) for x in children]
    self.assertTrue(u"aff4:/C.0000000000000000/fs/os/c/中国新闻网新闻中"
                    in urns)

    fd = aff4.FACTORY.Open(rdf_client.ClientURN(client_id).Add(
        "/fs/os/c/中国新闻网新闻中"), token=self.token)

    children = list(fd.OpenChildren())
    self.assertEqual(len(children), 1)
    child = children[0]
    self.assertEqual(child.Get(child.Schema.TYPE), "VFSFile")

    # This tests filtering through the AFF4Filter.
    fd = aff4.FACTORY.Open(rdf_client.ClientURN(client_id).Add(
        "/fs/os/c/bin %s" % client_id), token=self.token)

    matched = list(fd.Query(
        "subject matches '%s/r?bash'" % utils.EscapeRegex(fd.urn)))
    self.assertEqual(len(matched), 2)

    matched.sort(key=lambda x: str(x.urn))
    self.assertEqual(utils.SmartUnicode(matched[0].urn),
                     u"aff4:/C.0000000000000000/fs/os/"
                     u"c/bin C.0000000000000000/bash")
    self.assertEqual(utils.SmartUnicode(matched[1].urn),
                     u"aff4:/C.0000000000000000/fs/os/"
                     u"c/bin C.0000000000000000/rbash")

  def testQueryWithTimestamp(self):
    """Tests aff4 querying using timestamps."""
    # First we create a fixture
    client_id = "C.%016X" % 0
    test_lib.ClientFixture(client_id, token=self.token)

    file_url = rdf_client.ClientURN(client_id).Add("/fs/os/c/time/file.txt")
    for t in [1000, 1500, 2000, 2500]:
      with test_lib.FakeTime(t):
        f = aff4.FACTORY.Create(rdfvalue.RDFURN(file_url), "VFSFile",
                                token=self.token)
        f.write(str(t))
        f.Close()

    # The following tests occur sometime in the future (time 3000).
    with test_lib.FakeTime(3000):
      fd = aff4.FACTORY.Open(rdf_client.ClientURN(client_id).Add(
          "/fs/os/c/time"), token=self.token)

      # Query for all entries.
      matched = list(fd.Query(u"subject matches 'file'", age=aff4.ALL_TIMES))
      # A file and a MemoryStream containing the data.
      self.assertEqual(len(matched), 1)
      self.assertEqual(matched[0].read(100), "2500")

      # Query for the latest entry.
      matched = list(fd.Query(u"subject matches 'file'",
                              age=aff4.NEWEST_TIME))
      self.assertEqual(len(matched), 1)
      self.assertEqual(matched[0].read(100), "2500")

      # Query for a range 1250-2250.
      matched = list(fd.Query(u"subject matches 'file'",
                              age=(1250 * 1e6, 2250 * 1e6)))
      self.assertEqual(len(matched), 1)
      self.assertEqual(matched[0].read(100), "2000")

      # Query for a range 1750-3250.
      matched = list(fd.Query(u"subject matches 'file'",
                              age=(1750 * 1e6, 3250 * 1e6)))
      self.assertEqual(len(matched), 1)
      self.assertEqual(matched[0].read(100), "2500")

      # Query for a range 1600 and older.
      matched = list(fd.Query(u"subject matches 'file'", age=(0, 1600 * 1e6)))
      self.assertEqual(len(matched), 1)
      self.assertEqual(matched[0].read(100), "1500")

  def testMultiOpen(self):
    root_urn = aff4.ROOT_URN.Add("path")

    f = aff4.FACTORY.Create(root_urn.Add("some1"), "AFF4Volume",
                            token=self.token)
    f.Close()

    f = aff4.FACTORY.Create(root_urn.Add("some2"), "AFF4Volume",
                            token=self.token)
    f.Close()

    root = aff4.FACTORY.Open(root_urn, token=self.token)
    all_children = list(aff4.FACTORY.MultiOpen(root.ListChildren(),
                                               token=self.token))
    self.assertListEqual(sorted([x.urn for x in all_children]),
                         [root_urn.Add("some1"), root_urn.Add("some2")])

  def testObjectListChildren(self):
    root_urn = aff4.ROOT_URN.Add("path")

    f = aff4.FACTORY.Create(root_urn.Add("some1"), "AFF4Volume",
                            token=self.token)
    f.Close()

    f = aff4.FACTORY.Create(root_urn.Add("some2"), "AFF4Volume",
                            token=self.token)
    f.Close()

    root = aff4.FACTORY.Open(root_urn, token=self.token)
    all_children = sorted(list(root.ListChildren()))

    self.assertListEqual(sorted(all_children),
                         [root_urn.Add("some1"), root_urn.Add("some2")])

  def testMultiListChildren(self):
    client1_urn = rdfvalue.RDFURN("C.%016X" % 0)
    client2_urn = rdfvalue.RDFURN("C.%016X" % 1)

    with aff4.FACTORY.Create(client1_urn.Add("some1"), "AFF4Volume",
                             token=self.token):
      pass

    with aff4.FACTORY.Create(client2_urn.Add("some2"), "AFF4Volume",
                             token=self.token):
      pass

    children = dict(aff4.FACTORY.MultiListChildren([client1_urn, client2_urn],
                                                   token=self.token))

    self.assertListEqual(sorted(children.keys()),
                         [client1_urn, client2_urn])
    self.assertListEqual(children[client1_urn],
                         [client1_urn.Add("some1")])
    self.assertListEqual(children[client2_urn],
                         [client2_urn.Add("some2")])

  def testFactoryListChildren(self):
    client_urn = rdfvalue.RDFURN("C.%016X" % 0)

    with aff4.FACTORY.Create(client_urn.Add("some1"), "AFF4Volume",
                             token=self.token):
      pass

    with aff4.FACTORY.Create(client_urn.Add("some2"), "AFF4Volume",
                             token=self.token):
      pass

    children = aff4.FACTORY.ListChildren(client_urn, token=self.token)
    self.assertListEqual(sorted(children),
                         [client_urn.Add("some1"), client_urn.Add("some2")])

  def testIndexNotUpdatedWhenWrittenWithinIntermediateCacheAge(self):
    with utils.Stubber(time, "time", lambda: 100):
      fd = aff4.FACTORY.Create(
          self.client_id.Add("parent").Add("child1"),
          aff4_type="AFF4Volume", token=self.token)
      fd.Close()

    fd = aff4.FACTORY.Open(self.client_id, token=self.token)
    children = list(fd.ListChildren())
    self.assertEqual(len(children), 1)
    self.assertEqual(children[0].age,
                     rdfvalue.RDFDatetime().FromSecondsFromEpoch(100))

    latest_time = 100 + config_lib.CONFIG["AFF4.intermediate_cache_age"] - 1
    with utils.Stubber(time, "time", lambda: latest_time):
      fd = aff4.FACTORY.Create(
          self.client_id.Add("parent").Add("child2"),
          aff4_type="AFF4Volume", token=self.token)
      fd.Close()

    fd = aff4.FACTORY.Open(self.client_id, token=self.token)
    children = list(fd.ListChildren())
    self.assertEqual(len(children), 1)
    self.assertEqual(children[0].age,
                     rdfvalue.RDFDatetime().FromSecondsFromEpoch(100))

  def testIndexUpdatedWhenWrittenAfterIntemediateCacheAge(self):
    with utils.Stubber(time, "time", lambda: 100):
      fd = aff4.FACTORY.Create(
          self.client_id.Add("parent").Add("child1"),
          aff4_type="AFF4Volume", token=self.token)
      fd.Close()

    fd = aff4.FACTORY.Open(self.client_id, token=self.token)
    children = list(fd.ListChildren())
    self.assertEqual(len(children), 1)
    self.assertEqual(children[0].age,
                     rdfvalue.RDFDatetime().FromSecondsFromEpoch(100))

    latest_time = 100 + config_lib.CONFIG["AFF4.intermediate_cache_age"] + 1
    with utils.Stubber(time, "time", lambda: latest_time):
      fd = aff4.FACTORY.Create(
          self.client_id.Add("parent").Add("child2"),
          aff4_type="AFF4Volume", token=self.token)
      fd.Close()

    fd = aff4.FACTORY.Open(self.client_id, token=self.token)
    children = list(fd.ListChildren())
    self.assertEqual(len(children), 1)
    self.assertEqual(children[0].age,
                     rdfvalue.RDFDatetime().FromSecondsFromEpoch(latest_time))

  def testClose(self):
    """Ensure that closed objects can not be used again."""
    client = aff4.FACTORY.Create(self.client_id, "VFSGRRClient", mode="w",
                                 token=self.token)
    client.Close()

    self.assertRaises(IOError, client.Get, client.Schema.HOSTNAME)
    self.assertRaises(IOError, client.Set, client.Schema.HOSTNAME("hello"))

  def testVersionOrder(self):
    """Test that GetValuesForAttribute returns versions in the right order."""
    client = aff4.FACTORY.Create(self.client_id, "VFSGRRClient", mode="w",
                                 token=self.token)

    client.Set(client.Schema.HOSTNAME("Host1"))
    client.Flush()

    client.Set(client.Schema.HOSTNAME("Host2"))
    client.Flush()

    # Get() returns the most recent version.
    self.assertEqual(client.Get(client.Schema.HOSTNAME), "Host2")

    client = aff4.FACTORY.Open(self.client_id, token=self.token,
                               age=aff4.ALL_TIMES)

    # Versioned attributes must be returned in most recent order first.
    self.assertEqual(list(
        client.GetValuesForAttribute(client.Schema.HOSTNAME)),
                     ["Host2", "Host1"])

    # Get() returns the most recent version.
    self.assertEqual(client.Get(client.Schema.HOSTNAME), "Host2")

  def testAsynchronousOpenWithLockWorksCorrectly(self):
    self.client_id = rdfvalue.RDFURN(self.client_id)

    client = aff4.FACTORY.Create(self.client_id, "VFSGRRClient", mode="w",
                                 token=self.token)
    client.Set(client.Schema.HOSTNAME("client1"))
    client.Close()

    with aff4.FACTORY.OpenWithLock(self.client_id, token=self.token) as obj1:
      # Check that the object is correctly opened by reading the attribute
      self.assertEqual(obj1.Get(obj1.Schema.HOSTNAME), "client1")

      def TryOpen():
        with aff4.FACTORY.OpenWithLock(self.client_id, token=self.token,
                                       blocking=False):
          pass

      # This should raise, because obj1 is holding the lock
      self.assertRaises(aff4.LockError, TryOpen)

    # This shouldn't raise now, as previous Close() call has released the lock.
    with aff4.FACTORY.OpenWithLock(self.client_id, token=self.token,
                                   blocking=False):
      pass

  def testAsynchronousCreateWithLock(self):
    self.client_id = rdfvalue.RDFURN(self.client_id)

    with aff4.FACTORY.CreateWithLock(
        self.client_id, "VFSGRRClient", token=self.token) as obj:

      obj.Set(obj.Schema.HOSTNAME("client1"))

      def TryOpen():
        with aff4.FACTORY.OpenWithLock(self.client_id, token=self.token,
                                       blocking=False):
          pass

      # This should raise, because obj1 is holding the lock
      self.assertRaises(aff4.LockError, TryOpen)

    # This shouldn't raise now, as previous Close() call has released the lock.
    with aff4.FACTORY.OpenWithLock(self.client_id, token=self.token,
                                   blocking=False) as obj:
      # Check that the object is correctly opened by reading the attribute
      self.assertEqual(obj.Get(obj.Schema.HOSTNAME), "client1")

  def testSynchronousOpenWithLockWorksCorrectly(self):
    client = aff4.FACTORY.Create(self.client_id, "VFSGRRClient", mode="w",
                                 token=self.token)
    client.Set(client.Schema.HOSTNAME("client1"))
    client.Close()

    t_state = {"parallel_thread_got_lock": False,
               "parallel_thread_raised": False}

    def ParallelThread():
      try:
        # Using blocking_lock_timeout of 10 minutes to avoid possible
        # timeouts when running tests on slow hardware.
        with aff4.FACTORY.OpenWithLock(self.client_id, token=self.token,
                                       blocking=True, blocking_sleep_interval=0,
                                       blocking_lock_timeout=600):
          pass
        t_state["parallel_thread_got_lock"] = True
      except Exception:  # pylint: disable=broad-except
        # Catching all the exceptions, because exceptions raised in threads
        # do not cause the test to fail - threads just die silently.
        t_state["parallel_thread_raised"] = True

    t = threading.Thread(target=ParallelThread)

    with aff4.FACTORY.OpenWithLock(self.client_id, token=self.token) as obj1:
      # Check that the object is correctly opened by reading the attribute
      self.assertEqual(obj1.Get(obj1.Schema.HOSTNAME), "client1")

      t.start()
      time.sleep(0.1)
      # At this point, the thread should be attemting getting the lock.
      self.assertFalse(t_state["parallel_thread_got_lock"])
      self.assertFalse(t_state["parallel_thread_raised"])

    # We released the lock, so now the thread should finally get it,
    # release it, and die.
    t.join()
    self.assertTrue(t_state["parallel_thread_got_lock"])
    self.assertFalse(t_state["parallel_thread_raised"])

  def testSynchronousOpenWithLockTimesOutCorrectly(self):
    client = aff4.FACTORY.Create(self.client_id, "VFSGRRClient", mode="w",
                                 token=self.token)
    client.Set(client.Schema.HOSTNAME("client1"))
    client.Close()

    with aff4.FACTORY.OpenWithLock(self.client_id, token=self.token) as obj1:
      # Check that the object is correctly opened by reading the attribute
      self.assertEqual(obj1.Get(obj1.Schema.HOSTNAME), "client1")

      def TryOpen():
        with aff4.FACTORY.OpenWithLock(
            self.client_id, token=self.token,
            blocking=True, blocking_lock_timeout=0.1,
            blocking_sleep_interval=0.1):
          pass

      self.assertRaises(aff4.LockError, TryOpen)

  def testLockHasLimitedLeaseTime(self):
    with test_lib.FakeTime(100):
      client = aff4.FACTORY.Create(self.client_id, "VFSGRRClient", mode="w",
                                   token=self.token)
      client.Set(client.Schema.HOSTNAME("client1"))
      client.Close()

      with self.assertRaises(aff4.LockError):
        with aff4.FACTORY.OpenWithLock(self.client_id, token=self.token,
                                       lease_time=100) as fd:

          def TryOpen():
            with aff4.FACTORY.OpenWithLock(self.client_id, token=self.token,
                                           blocking=False):
              pass

          time.time = lambda: 150
          self.assertRaises(aff4.LockError, TryOpen)

          # This shouldn't raise, because previous lock's lease has expired
          time.time = lambda: 201
          TryOpen()

          self.assertRaises(aff4.LockError, fd.Close)
          self.assertRaises(aff4.LockError, fd.Flush)

  def testUpdateLeaseRaisesIfObjectIsNotLocked(self):
    client = aff4.FACTORY.Create(self.client_id, "VFSGRRClient", mode="w",
                                 token=self.token)
    client.Set(client.Schema.HOSTNAME("client1"))
    client.Close()

    client = aff4.FACTORY.Open(self.client_id, token=self.token)
    self.assertRaises(aff4.LockError, client.UpdateLease, 100)

  def testUpdateLeaseRaisesIfLeaseHasExpired(self):
    with test_lib.FakeTime(100):
      client = aff4.FACTORY.Create(self.client_id, "VFSGRRClient", mode="w",
                                   token=self.token)
      client.Set(client.Schema.HOSTNAME("client1"))
      client.Close()

      try:
        with aff4.FACTORY.OpenWithLock(self.client_id, token=self.token,
                                       lease_time=100) as fd:
          time.time = lambda: 250
          self.assertRaises(aff4.LockError, fd.UpdateLease, 100)
      except aff4.LockError:
        # LockContextManager.__exit__ calls Close(), which calls Flush(),
        # which calls CheckLease(), which raises LockError because the lease
        # time has expired. Ignoring this exception.
        pass

  def testCheckLease(self):
    with test_lib.FakeTime(100):
      client = aff4.FACTORY.Create(self.client_id, "VFSGRRClient", mode="w",
                                   token=self.token)
      client.Set(client.Schema.HOSTNAME("client1"))
      client.Close()

      with self.assertRaises(aff4.LockError):
        with aff4.FACTORY.OpenWithLock(self.client_id, token=self.token,
                                       lease_time=300) as fd:
          self.assertTrue(fd.CheckLease())
          time.time = lambda: 500
          self.assertEqual(fd.CheckLease(), 0)

  def testUpdateLeaseWorksCorrectly(self):
    with test_lib.FakeTime(100):
      client = aff4.FACTORY.Create(self.client_id, "VFSGRRClient", mode="w",
                                   token=self.token)
      client.Set(client.Schema.HOSTNAME("client1"))
      client.Close()

      with aff4.FACTORY.OpenWithLock(self.client_id, token=self.token,
                                     lease_time=100) as fd:
        fd.UpdateLease(200)
        time.time = lambda: 250

        # If lease is updated correctly, object can't be OpenedWithLock again,
        # because it's already locked and lease hasn't expired.
        def TryOpen():
          with aff4.FACTORY.OpenWithLock(self.client_id, token=self.token,
                                         blocking=False):
            pass

        self.assertRaises(aff4.LockError, TryOpen)

  def testLockProtectedAttributesWorkCorrectly(self):
    obj = aff4.FACTORY.Create("aff4:/obj", "ObjectWithLockProtectedAttribute",
                              token=self.token)
    obj.Close()

    # Lock-protected attribute can't be set when plain Open() is used.
    obj = aff4.FACTORY.Open("aff4:/obj", mode="rw", token=self.token)
    obj.Set(obj.Schema.UNPROTECTED_ATTR("value"))
    self.assertRaises(IOError, obj.Set,
                      obj.Schema.LOCK_PROTECTED_ATTR("value"))
    obj.Close()

    # Lock-protected attribute is successfully set, because the object is
    # locked with OpenWithLock().
    with aff4.FACTORY.OpenWithLock("aff4:/obj", token=self.token) as obj:
      obj.Set(obj.Schema.UNPROTECTED_ATTR("value"))
      obj.Set(obj.Schema.LOCK_PROTECTED_ATTR("value"))

    # We can't respect locks during blind-write operations.
    obj = aff4.FACTORY.Create("aff4:/obj", "ObjectWithLockProtectedAttribute",
                              token=self.token)
    obj.Set(obj.Schema.UNPROTECTED_ATTR("value"))
    obj.Set(obj.Schema.LOCK_PROTECTED_ATTR("value"))
    obj.Close()

  def testAddLabelsCallAddsMultipleLabels(self):
    """Check we can set and remove labels."""
    with aff4.FACTORY.Create("C.0000000000000001", "VFSGRRClient",
                             mode="rw", token=self.token) as client:
      labels = ["label1", "label2", "label3"]
      client.AddLabels(*labels)

      # Check that labels are correctly set in the current object.
      self.assertListEqual(labels, client.GetLabelsNames())

    # Check that labels are correctly set in the object that is fresh from the
    # data store.
    client = aff4.FACTORY.Open("C.0000000000000001", token=self.token)
    self.assertListEqual(labels, client.GetLabelsNames())

  def testRemoveLabelsCallRemovesMultipleLabels(self):
    with aff4.FACTORY.Create("C.0000000000000001", "VFSGRRClient",
                             mode="rw", token=self.token) as client:
      labels = ["label1", "label2", "label3"]
      client.AddLabels(*labels)

    with aff4.FACTORY.Create("C.0000000000000001", "VFSGRRClient",
                             mode="rw", token=self.token) as client:
      client.RemoveLabels("label1")

    self.assertEqual(["label2", "label3"],
                     list(client.GetLabelsNames()))

  def testPathSpecInterpolation(self):
    # Create a base directory containing a pathspec.
    os_urn = rdfvalue.RDFURN("aff4:/C.0000000000000002/fs/os")
    pathspec = rdf_paths.PathSpec(
        path="/", pathtype=rdf_paths.PathSpec.PathType.OS)
    additional_path = "/var/log"
    fd = aff4.FACTORY.Create(os_urn, "VFSDirectory", token=self.token)
    fd.Set(fd.Schema.PATHSPEC(pathspec))
    fd.Close()

    # Now we open a path below this aff4 directory.
    fd = aff4.FACTORY.Create(os_urn.Add(additional_path), "VFSDirectory",
                             mode="rw", token=self.token)
    flow_id = fd.Update(attribute="CONTAINS")

    flow_obj = aff4.FACTORY.Open(flow_id, token=self.token)
    self.assertEqual(flow_obj.args.pathspec.pathtype, pathspec.pathtype)
    self.assertEqual(flow_obj.args.pathspec.CollapsePath(), additional_path)


class AFF4SymlinkTestSubject(aff4.AFF4Volume):
  """A test subject for AFF4SymlinkTest."""

  class SchemaCls(aff4.AFF4Object.SchemaCls):
    SOME_STRING = aff4.Attribute("metadata:some_string",
                                 rdfvalue.RDFString,
                                 "SomeString")

  def Initialize(self):
    self.test_var = 42

  def testMethod(self):
    return str(self.Get(self.Schema.SOME_STRING)) + "-suffix"


class AFF4SymlinkTest(test_lib.AFF4ObjectTest):
  """Tests the AFF4Symlink."""

  symlink_source_urn = rdfvalue.RDFURN("aff4:/symlink")
  symlink_target_urn = rdfvalue.RDFURN("aff4:/C.0000000000000001")

  def CreateAndOpenObjectAndSymlink(self):
    with aff4.FACTORY.Create(self.symlink_target_urn, "AFF4SymlinkTestSubject",
                             token=self.token) as fd:
      fd.Set(fd.Schema.SOME_STRING, rdfvalue.RDFString("the_string"))

    with aff4.FACTORY.Create(self.symlink_source_urn, "AFF4Symlink",
                             token=self.token) as symlink:
      symlink.Set(symlink.Schema.SYMLINK_TARGET, self.symlink_target_urn)

    fd = aff4.FACTORY.Open(self.symlink_target_urn, token=self.token)
    symlink = aff4.FACTORY.Open(self.symlink_source_urn, token=self.token)

    return (fd, symlink)

  def testOpenedSymlinkUrnIsEqualToTargetUrn(self):
    fd, symlink_obj = self.CreateAndOpenObjectAndSymlink()

    self.assertEqual(symlink_obj.urn, fd.urn)

  def testOpenedObjectHasSymlinkUrnAttributeSet(self):
    _, symlink_obj = self.CreateAndOpenObjectAndSymlink()

    self.assertIsNotNone(symlink_obj.symlink_urn)
    self.assertEqual(symlink_obj.urn, self.symlink_target_urn)
    self.assertEqual(symlink_obj.symlink_urn, self.symlink_source_urn)

  def testMultiOpenMixedObjects(self):
    """Test symlinks are correct when using multiopen with other objects."""
    fd, _ = self.CreateAndOpenObjectAndSymlink()
    fd_urn1 = fd.urn

    fd_urn2 = rdfvalue.RDFURN("aff4:/C.0000000000000002")
    fd = aff4.FACTORY.Create(fd_urn2, "AFF4Image",
                             token=self.token)
    fd.Close()

    for fd in aff4.FACTORY.MultiOpen([self.symlink_source_urn, fd_urn2],
                                     token=self.token):
      if fd.urn == fd_urn2:
        self.assertTrue(isinstance(fd, aff4.AFF4Image))
      elif fd.urn == fd_urn1:
        self.assertTrue(isinstance(fd, AFF4SymlinkTestSubject))
        self.assertIsNotNone(fd.symlink_urn)
        self.assertEqual(fd.urn, self.symlink_target_urn)
        self.assertEqual(fd.symlink_urn, self.symlink_source_urn)
      else:
        raise ValueError("Unexpected URN: %s" % fd.urn)

  def testMultiOpenMixedObjectWithCheckedAff4Type(self):
    fd, _ = self.CreateAndOpenObjectAndSymlink()

    fd_urn2 = rdfvalue.RDFURN("aff4:/C.0000000000000002")
    fd = aff4.FACTORY.Create(fd_urn2, "AFF4Image",
                             token=self.token)
    fd.Close()

    # AFF4Image object should be ignored due to aff4_type check.
    # At the same, type check shouldn't filter out the symlink,
    # but should check the symlinked object.
    fds = list(aff4.FACTORY.MultiOpen([self.symlink_source_urn, fd_urn2],
                                      aff4_type="AFF4SymlinkTestSubject",
                                      token=self.token))
    self.assertEqual(len(fds), 1)
    self.assertTrue(isinstance(fds[0], AFF4SymlinkTestSubject))

    # AFF4Image should be returned, but symlinked AFF4SymlinkTestSubject should
    # get filtered out due to aff4_type restriction.
    fds = list(aff4.FACTORY.MultiOpen([self.symlink_source_urn, fd_urn2],
                                      aff4_type="AFF4Image",
                                      token=self.token))
    self.assertEqual(len(fds), 1)
    self.assertTrue(isinstance(fds[0], aff4.AFF4Image))

  def testOpenedSymlinkAFF4AttributesAreEqualToTarget(self):
    fd, symlink_obj = self.CreateAndOpenObjectAndSymlink()

    for attr in fd.Schema.ListAttributes():
      self.assertEqual(symlink_obj.Get(attr), fd.Get(attr))


class ForemanTests(test_lib.AFF4ObjectTest):
  """Tests the Foreman."""

  clients_launched = []

  def setUp(self):
    super(ForemanTests, self).setUp()
    aff4_grr.GRRAFF4Init().Run()

  def StartFlow(self, client_id, flow_name, token=None, **kw):
    # Make sure the foreman is launching these
    self.assertEqual(token.username, "Foreman")

    # Make sure we pass the argv along
    self.assertEqual(kw["foo"], "bar")

    # Keep a record of all the clients
    self.clients_launched.append((client_id, flow_name))

  def testOperatingSystemSelection(self):
    """Tests that we can distinguish based on operating system."""
    fd = aff4.FACTORY.Create("C.0000000000000001", "VFSGRRClient",
                             token=self.token)
    fd.Set(fd.Schema.SYSTEM, rdfvalue.RDFString("Windows XP"))
    fd.Close()

    fd = aff4.FACTORY.Create("C.0000000000000002", "VFSGRRClient",
                             token=self.token)
    fd.Set(fd.Schema.SYSTEM, rdfvalue.RDFString("Linux"))
    fd.Close()

    fd = aff4.FACTORY.Create("C.0000000000000003", "VFSGRRClient",
                             token=self.token)
    fd.Set(fd.Schema.SYSTEM, rdfvalue.RDFString("Windows 7"))
    fd.Close()

    with utils.Stubber(flow.GRRFlow, "StartFlow", self.StartFlow):
      # Now setup the filters
      now = time.time() * 1e6
      expires = (time.time() + 3600) * 1e6
      foreman = aff4.FACTORY.Open("aff4:/foreman", mode="rw", token=self.token)

      # Make a new rule
      rule = rdf_foreman.ForemanRule(created=int(now), expires=int(expires),
                                     description="Test rule")

      # Matches Windows boxes
      rule.regex_rules.Append(attribute_name=fd.Schema.SYSTEM.name,
                              attribute_regex="Windows")

      # Will run Test Flow
      rule.actions.Append(flow_name="Test Flow",
                          argv=rdf_protodict.Dict(foo="bar"))

      # Clear the rule set and add the new rule to it.
      rule_set = foreman.Schema.RULES()
      rule_set.Append(rule)

      # Assign it to the foreman
      foreman.Set(foreman.Schema.RULES, rule_set)
      foreman.Close()

      self.clients_launched = []
      foreman.AssignTasksToClient("C.0000000000000001")
      foreman.AssignTasksToClient("C.0000000000000002")
      foreman.AssignTasksToClient("C.0000000000000003")

      # Make sure that only the windows machines ran
      self.assertEqual(len(self.clients_launched), 2)
      self.assertEqual(self.clients_launched[0][0],
                       rdf_client.ClientURN("C.0000000000000001"))
      self.assertEqual(self.clients_launched[1][0],
                       rdf_client.ClientURN("C.0000000000000003"))

      self.clients_launched = []

      # Run again - This should not fire since it did already
      foreman.AssignTasksToClient("C.0000000000000001")
      foreman.AssignTasksToClient("C.0000000000000002")
      foreman.AssignTasksToClient("C.0000000000000003")

      self.assertEqual(len(self.clients_launched), 0)

  def testIntegerComparisons(self):
    """Tests that we can use integer matching rules on the foreman."""

    fd = aff4.FACTORY.Create("C.0000000000000011", "VFSGRRClient",
                             token=self.token)
    fd.Set(fd.Schema.SYSTEM, rdfvalue.RDFString("Windows XP"))
    fd.Set(fd.Schema.INSTALL_DATE(1336480583077736))
    fd.Close()

    fd = aff4.FACTORY.Create("C.0000000000000012", "VFSGRRClient",
                             token=self.token)
    fd.Set(fd.Schema.SYSTEM, rdfvalue.RDFString("Windows 7"))
    fd.Set(fd.Schema.INSTALL_DATE(1336480583077736))
    fd.Close()

    fd = aff4.FACTORY.Create("C.0000000000000013", "VFSGRRClient",
                             token=self.token)
    fd.Set(fd.Schema.SYSTEM, rdfvalue.RDFString("Windows 7"))
    # This one was installed one week earlier.
    fd.Set(fd.Schema.INSTALL_DATE(1336480583077736 - 7 * 24 * 3600 * 1e6))
    fd.Close()

    fd = aff4.FACTORY.Create("C.0000000000000014", "VFSGRRClient",
                             token=self.token)
    fd.Set(fd.Schema.SYSTEM, rdfvalue.RDFString("Windows 7"))
    fd.Set(fd.Schema.LAST_BOOT_TIME(1336300000000000))
    fd.Close()

    with utils.Stubber(flow.GRRFlow, "StartFlow", self.StartFlow):
      # Now setup the filters
      now = time.time() * 1e6
      expires = (time.time() + 3600) * 1e6
      foreman = aff4.FACTORY.Open("aff4:/foreman", mode="rw", token=self.token)

      # Make a new rule
      rule = rdf_foreman.ForemanRule(created=int(now), expires=int(expires),
                                     description="Test rule(old)")

      # Matches the old client
      rule.integer_rules.Append(
          attribute_name=fd.Schema.INSTALL_DATE.name,
          operator=rdf_foreman.ForemanAttributeInteger.Operator.LESS_THAN,
          value=int(1336480583077736 - 3600 * 1e6))

      old_flow = "Test flow for old clients"
      # Will run Test Flow
      rule.actions.Append(flow_name=old_flow,
                          argv=rdf_protodict.Dict(dict(foo="bar")))

      # Clear the rule set and add the new rule to it.
      rule_set = foreman.Schema.RULES()
      rule_set.Append(rule)

      # Make a new rule
      rule = rdf_foreman.ForemanRule(created=int(now), expires=int(expires),
                                     description="Test rule(new)")

      # Matches the newer clients
      rule.integer_rules.Append(
          attribute_name=fd.Schema.INSTALL_DATE.name,
          operator=rdf_foreman.ForemanAttributeInteger.Operator.GREATER_THAN,
          value=int(1336480583077736 - 3600 * 1e6))

      new_flow = "Test flow for newer clients"

      # Will run Test Flow
      rule.actions.Append(flow_name=new_flow,
                          argv=rdf_protodict.Dict(dict(foo="bar")))

      rule_set.Append(rule)

      # Make a new rule
      rule = rdf_foreman.ForemanRule(created=int(now), expires=int(expires),
                                     description="Test rule(eq)")

      # Note that this also tests the handling of nonexistent attributes.
      rule.integer_rules.Append(
          attribute_name=fd.Schema.LAST_BOOT_TIME.name,
          operator=rdf_foreman.ForemanAttributeInteger.Operator.EQUAL,
          value=1336300000000000)

      eq_flow = "Test flow for LAST_BOOT_TIME"

      rule.actions.Append(flow_name=eq_flow,
                          argv=rdf_protodict.Dict(dict(foo="bar")))

      rule_set.Append(rule)

      # Assign it to the foreman
      foreman.Set(foreman.Schema.RULES, rule_set)
      foreman.Close()

      self.clients_launched = []
      foreman.AssignTasksToClient("C.0000000000000011")
      foreman.AssignTasksToClient("C.0000000000000012")
      foreman.AssignTasksToClient("C.0000000000000013")
      foreman.AssignTasksToClient("C.0000000000000014")

      # Make sure that the clients ran the correct flows.
      self.assertEqual(len(self.clients_launched), 4)
      self.assertEqual(self.clients_launched[0][0],
                       rdf_client.ClientURN("C.0000000000000011"))
      self.assertEqual(self.clients_launched[0][1], new_flow)
      self.assertEqual(self.clients_launched[1][0],
                       rdf_client.ClientURN("C.0000000000000012"))
      self.assertEqual(self.clients_launched[1][1], new_flow)
      self.assertEqual(self.clients_launched[2][0],
                       rdf_client.ClientURN("C.0000000000000013"))
      self.assertEqual(self.clients_launched[2][1], old_flow)
      self.assertEqual(self.clients_launched[3][0],
                       rdf_client.ClientURN("C.0000000000000014"))
      self.assertEqual(self.clients_launched[3][1], eq_flow)

  def testRuleExpiration(self):
    with test_lib.FakeTime(1000):
      foreman = aff4.FACTORY.Open("aff4:/foreman", mode="rw", token=self.token)

      rules = []
      rules.append(rdf_foreman.ForemanRule(created=1000 * 1000000,
                                           expires=1500 * 1000000,
                                           description="Test rule1"))
      rules.append(rdf_foreman.ForemanRule(created=1000 * 1000000,
                                           expires=1200 * 1000000,
                                           description="Test rule2"))
      rules.append(rdf_foreman.ForemanRule(created=1000 * 1000000,
                                           expires=1500 * 1000000,
                                           description="Test rule3"))
      rules.append(rdf_foreman.ForemanRule(created=1000 * 1000000,
                                           expires=1300 * 1000000,
                                           description="Test rule4"))

      client_id = "C.0000000000000021"
      fd = aff4.FACTORY.Create(client_id, "VFSGRRClient",
                               token=self.token)
      fd.Close()

      # Clear the rule set and add the new rules to it.
      rule_set = foreman.Schema.RULES()
      for rule in rules:
        # Add some regex that does not match the client.
        rule.regex_rules.Append(attribute_name=fd.Schema.SYSTEM.name,
                                attribute_regex="XXX")
        rule_set.Append(rule)
      foreman.Set(foreman.Schema.RULES, rule_set)
      foreman.Close()

    fd = aff4.FACTORY.Create(client_id, "VFSGRRClient",
                             token=self.token)
    for now, num_rules in [(1000, 4), (1250, 3), (1350, 2), (1600, 0)]:
      with test_lib.FakeTime(now):
        fd.Set(fd.Schema.LAST_FOREMAN_TIME(100))
        fd.Flush()
        foreman = aff4.FACTORY.Open("aff4:/foreman", mode="rw",
                                    token=self.token)
        foreman.AssignTasksToClient(client_id)
        rules = foreman.Get(foreman.Schema.RULES)
        self.assertEqual(len(rules), num_rules)


class AFF4TestLoader(test_lib.GRRTestLoader):
  base_class = test_lib.AFF4ObjectTest


def main(argv):
  # Run the full test suite
  test_lib.GrrTestProgram(argv=argv, testLoader=AFF4TestLoader())

if __name__ == "__main__":
  flags.StartMain(main)
