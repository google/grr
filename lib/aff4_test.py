#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

"""Tests for the flow."""


import threading
import time

# pylint: disable=unused-import,g-bad-import-order
from grr.lib import server_plugins
# Import this so the aff4 tests will be run.
from grr.lib.aff4_objects import tests
# pylint: enable=unused-import,g-bad-import-order

from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import flags
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib import utils
from grr.lib.aff4_objects import aff4_grr


class MockNotificationRule(aff4.AFF4NotificationRule):
  OBJECTS_WRITTEN = []

  def OnWriteObject(self, aff4_object):
    MockNotificationRule.OBJECTS_WRITTEN.append(aff4_object)


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


class AFF4Tests(test_lib.AFF4ObjectTest):
  """Test the AFF4 abstraction."""

  def setUp(self):
    super(AFF4Tests, self).setUp()
    # TODO(user): remove when everything is URN.
    self.client_id = rdfvalue.RDFURN(self.client_id)
    MockNotificationRule.OBJECTS_WRITTEN = []

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

    # There should also only be once clock attribute
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

  def testAppendAttribute(self):
    """Test that append attribute works."""
    # Create an object to carry attributes
    obj = aff4.FACTORY.Create("foobar", "AFF4Object", token=self.token)
    obj.Set(obj.Schema.STORED("http://www.google.com"))
    obj.Close()

    obj = aff4.FACTORY.Open("foobar", mode="rw", token=self.token,
                            age=aff4.ALL_TIMES)
    self.assertEqual(1, len(list(obj.GetValuesForAttribute(obj.Schema.STORED))))

    # Add a bunch of attributes now.
    for i in range(5):
      obj.AddAttribute(obj.Schema.STORED("http://example.com/%s" % i))

    # There should be 6 there now
    self.assertEqual(6, len(list(obj.GetValuesForAttribute(obj.Schema.STORED))))
    obj.Close()

    # Check that when read back from the data_store we stored them all
    obj = aff4.FACTORY.Open("foobar", token=self.token, age=aff4.ALL_TIMES)
    self.assertEqual(6, len(list(obj.GetValuesForAttribute(obj.Schema.STORED))))

  def testCopyAttributes(self):
    # Create an object to carry attributes
    obj = aff4.FACTORY.Create("foobar", "AFF4Object", token=self.token)
    # Add a bunch of attributes now.
    for i in range(5):
      obj.AddAttribute(obj.Schema.STORED("http://example.com/%s" % i))
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
    obj.Set(obj.Schema.STORED("http://www.google.com"))
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
      self.assert_(int(last) > 1330354592221974)

  def testClientObject(self):
    fd = aff4.FACTORY.Create(self.client_id, "VFSGRRClient", token=self.token)

    # Certs invalid - The RDFX509Cert should check the validity of the cert
    self.assertRaises(rdfvalue.DecodeError, rdfvalue.RDFX509Cert, "My cert")

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

  def testAFF4Image(self):
    """Test the AFF4Image object."""
    path = "/C.12345/aff4image"

    fd = aff4.FACTORY.Create(path, "AFF4Image", token=self.token)
    fd.SetChunksize(10)

    # Make lots of small writes - The length of this string and the chunk size
    # are relative primes for worst case.
    for i in range(100):
      fd.Write("Test%08X\n" % i)

    fd.Close()

    fd = aff4.FACTORY.Open(path, token=self.token)
    for i in range(100):
      self.assertEqual(fd.Read(13), "Test%08X\n" % i)

    fd.Close()

    fd = aff4.FACTORY.Create(path, "AFF4Image", mode="rw", token=self.token)
    fd.Set(fd.Schema._CHUNKSIZE(10))

    # Overflow the cache.
    fd.Write("X" * 10000)
    self.assertEqual(fd.size, 10000)
    # Now rewind a bit and write something.
    fd.seek(fd.size - 100)
    fd.Write("Hello World")
    self.assertEqual(fd.size, 10000)
    # Now append to the end.
    fd.seek(fd.size)
    fd.Write("Y" * 100)
    self.assertEqual(fd.size, 10100)
    # And verify everything worked as expected.
    fd.seek(10000 - 200)
    data = fd.Read(500)
    self.assertEqual(len(data), 300)
    self.assertTrue("XXXHello WorldXXX" in data)
    self.assertTrue("XXXYYY" in data)

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

  def WriteImage(self, path, prefix="Test", timestamp=0):
    old_time = time.time
    try:
      time.time = lambda: timestamp
      fd = aff4.FACTORY.Create(path, "AFF4Image", mode="w", token=self.token)
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

    finally:
      time.time = old_time

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

  def testAFF4FlowObject(self):
    """Test the AFF4 Flow switch and object."""
    client = aff4.FACTORY.Create(self.client_id, "VFSGRRClient",
                                 token=self.token)
    client.Close()

    # Start some new flows on it
    session_ids = [flow.GRRFlow.StartFlow(self.client_id, "FlowOrderTest",
                                          token=self.token)
                   for _ in range(10)]

    # Try to open a single flow.
    flow_obj = aff4.FACTORY.Open(session_ids[0], mode="r", token=self.token)

    self.assertEqual(flow_obj.state.context.flow_name, "FlowOrderTest")
    self.assertEqual(flow_obj.session_id, session_ids[0])

    self.assertEqual(flow_obj.__class__.__name__, "FlowOrderTest")

    # Now load multiple flows at once
    client = aff4.FACTORY.Open(self.client_id, token=self.token,
                               age=aff4.ALL_TIMES)

    # This was removed...
    for f in client.GetValuesForAttribute(client.Schema.FLOW):
      session_ids.remove(f)

    # Did we get them all?
    self.assertEqual(session_ids, [])

  def testQuery(self):
    """Test the AFF4Collection object."""
    # First we create a fixture
    client_id = "C.%016X" % 0
    test_lib.ClientFixture(client_id, token=self.token)

    fd = aff4.FACTORY.Open(aff4.ROOT_URN.Add(client_id).Add(
        "/fs/os/c"), token=self.token)

    # Test that we can match a unicode char
    matched = list(fd.Query(u"subject matches '中'"))
    self.assertEqual(len(matched), 1)
    self.assertEqual(utils.SmartUnicode(matched[0].urn),
                     u"aff4:/C.0000000000000000/"
                     u"fs/os/c/中国新闻网新闻中")

    # Test that we can match a unicode char
    matched = list(fd.Query(ur"subject matches '\]\['"))
    self.assertEqual(len(matched), 1)
    self.assertEqual(utils.SmartUnicode(matched[0].urn),
                     u"aff4:/C.0000000000000000/"
                     u"fs/os/c/regex.*?][{}--")

    # Test the OpenChildren function on files that contain regex chars.
    fd = aff4.FACTORY.Open(aff4.ROOT_URN.Add(client_id).Add(
        r"/fs/os/c/regex\V.*?]xx[{}--"), token=self.token)

    children = list(fd.OpenChildren())
    self.assertEqual(len(children), 1)
    self.assertTrue("regexchild" in utils.SmartUnicode(children[0].urn))

    # Test that OpenChildren works correctly on Unicode names.
    fd = aff4.FACTORY.Open(aff4.ROOT_URN.Add(client_id).Add(
        "/fs/os/c"), token=self.token)

    children = list(fd.OpenChildren())
    # All children must have a valid type.
    for child in children:
      self.assertNotEqual(child.Get(child.Schema.TYPE), "VFSVolume")

    urns = [utils.SmartUnicode(x.urn) for x in children]

    self.assertTrue(u"aff4:/C.0000000000000000/fs/os/c/中国新闻网新闻中"
                    in urns)

    fd = aff4.FACTORY.Open(aff4.ROOT_URN.Add(client_id).Add(
        "/fs/os/c/中国新闻网新闻中"), token=self.token)

    children = list(fd.OpenChildren())
    self.assertEqual(len(children), 1)
    child = children[0]
    self.assertEqual(child.Get(child.Schema.TYPE), "VFSFile")

    # This tests the VFSDirectory implementation of Query (i.e. filtering
    # through the AFF4Filter).
    fd = aff4.FACTORY.Open(aff4.ROOT_URN.Add(client_id).Add(
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

    # This tests the native filtering through the database.
    fd = aff4.FACTORY.Open(aff4.ROOT_URN.Add(client_id), token=self.token)

    # Deliberately call the baseclass Query to search in the database.
    matched = list(aff4.AFF4Volume.Query(
        fd, u"subject matches '中国新闻网新闻中'"))

    self.assertEqual(len(matched), 2)
    self.assertEqual(utils.SmartUnicode(matched[0].urn),
                     u"aff4:/C.0000000000000000/"
                     u"fs/os/c/中国新闻网新闻中")

  def testQueryWithTimestamp(self):
    """Tests aff4 querying using timestamps."""
    # First we create a fixture
    client_id = "C.%016X" % 0
    test_lib.ClientFixture(client_id, token=self.token)

    old_time = time.time
    try:
      file_url = aff4.ROOT_URN.Add(client_id).Add("/fs/os/c/time/file.txt")
      for t in [1000, 1500, 2000, 2500]:
        time.time = lambda: t

        f = aff4.FACTORY.Create(rdfvalue.RDFURN(file_url), "VFSFile",
                                token=self.token)
        f.write(str(t))
        f.Close()

      fd = aff4.FACTORY.Open(aff4.ROOT_URN.Add(client_id).Add(
          "/fs/os/c/time"), token=self.token)

      # Query for all entries.
      matched = list(fd.Query(u"subject matches 'file'", age=aff4.ALL_TIMES))
      # A file and a MemoryStream containing the data.
      self.assertEqual(len(matched), 2)
      self.assertEqual(matched[0].read(100), "2500")

      # Query for the latest entry.
      matched = list(fd.Query(u"subject matches 'file'", age=aff4.NEWEST_TIME))
      self.assertEqual(len(matched), 2)
      self.assertEqual(matched[0].read(100), "2500")

      # Query for a range 1250-2250.
      matched = list(fd.Query(u"subject matches 'file'",
                              age=(1250 * 1e6, 2250 * 1e6)))
      self.assertEqual(len(matched), 2)
      self.assertEqual(matched[0].read(100), "2000")

      # Query for a range 1750-3250.
      matched = list(fd.Query(u"subject matches 'file'",
                              age=(1750 * 1e6, 3250 * 1e6)))
      self.assertEqual(len(matched), 2)
      self.assertEqual(matched[0].read(100), "2500")

      # Query for a range 1600 and older.
      matched = list(fd.Query(u"subject matches 'file'", age=(0, 1600 * 1e6)))
      self.assertEqual(len(matched), 2)
      self.assertEqual(matched[0].read(100), "1500")

    finally:
      time.time = old_time

  def testChangeNotifications(self):
    rule_fd = aff4.FACTORY.Create(
        rdfvalue.RDFURN("aff4:/config/aff4_rules/new_rule"),
        aff4_type="MockNotificationRule",
        token=self.token)
    rule_fd.Close()

    aff4.FACTORY.UpdateNotificationRules()

    fd = aff4.FACTORY.Create(
        rdfvalue.RDFURN("aff4:/some"),
        aff4_type="AFF4Object",
        token=self.token)
    fd.Close()

    self.assertEquals(len(MockNotificationRule.OBJECTS_WRITTEN), 1)
    self.assertEquals(MockNotificationRule.OBJECTS_WRITTEN[0].urn,
                      rdfvalue.RDFURN("aff4:/some"))

  def testNotificationRulesArePeriodicallyUpdated(self):
    current_time = time.time()
    time_in_future = (
        current_time +
        config_lib.CONFIG["AFF4.notification_rules_cache_age"] + 1)
    old_time = time.time
    try:
      # Be sure that we're well in advance from the time when aff4.FACTORY
      # got intialized.
      time.time = lambda: time_in_future

      fd = aff4.FACTORY.Create(
          rdfvalue.RDFURN("aff4:/some"),
          aff4_type="AFF4Object",
          token=self.token)
      fd.Close()

      # There are no rules set up yet.
      self.assertEquals(len(MockNotificationRule.OBJECTS_WRITTEN), 0)

      # Settin up the rule.
      rule_fd = aff4.FACTORY.Create(
          rdfvalue.RDFURN("aff4:/config/aff4_rules/new_rule"),
          aff4_type="MockNotificationRule",
          token=self.token)
      rule_fd.Close()

      fd = aff4.FACTORY.Create(
          rdfvalue.RDFURN("aff4:/some"),
          aff4_type="AFF4Object",
          token=self.token)
      fd.Close()

      # Rules were not reloaded yet.
      self.assertEquals(len(MockNotificationRule.OBJECTS_WRITTEN), 0)

      t = (time_in_future +
           config_lib.CONFIG["AFF4.notification_rules_cache_age"] - 1)
      time.time = lambda: t
      fd = aff4.FACTORY.Create(
          rdfvalue.RDFURN("aff4:/some"),
          aff4_type="AFF4Object",
          token=self.token)
      fd.Close()

      # It's still too early to reload the rules.
      self.assertEquals(len(MockNotificationRule.OBJECTS_WRITTEN), 0)

      t = (time_in_future +
           config_lib.CONFIG["AFF4.notification_rules_cache_age"] + 1)

      time.time = lambda: t
      fd = aff4.FACTORY.Create(
          rdfvalue.RDFURN("aff4:/some"),
          aff4_type="AFF4Object",
          token=self.token)
      fd.Close()

      # Rules have been already reloaded.
      self.assertEquals(len(MockNotificationRule.OBJECTS_WRITTEN), 1)
    finally:
      time.time = old_time

  def testListChildren(self):
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
    client1 = "C.%016X" % 0
    client2 = "C.%016X" % 1
    client1_urn = rdfvalue.RDFURN(client1)
    client2_urn = rdfvalue.RDFURN(client2)

    f = aff4.FACTORY.Create(client1_urn.Add("some1"), "AFF4Volume",
                            token=self.token)
    f.Close()

    f = aff4.FACTORY.Create(client2_urn.Add("some2"), "AFF4Volume",
                            token=self.token)
    f.Close()

    children = aff4.FACTORY.MultiListChildren([client1_urn, client2_urn],
                                              token=self.token)

    self.assertListEqual(sorted(children.keys()),
                         [client1_urn, client2_urn])
    self.assertListEqual(children[client1_urn],
                         [client1_urn.Add("some1")])
    self.assertListEqual(children[client2_urn],
                         [client2_urn.Add("some2")])

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
    self.assertEquals(client.Get(client.Schema.HOSTNAME), "Host2")

    client = aff4.FACTORY.Open(self.client_id, token=self.token,
                               age=aff4.ALL_TIMES)

    # Versioned attributes must be returned in most recent order first.
    self.assertEquals(list(
        client.GetValuesForAttribute(client.Schema.HOSTNAME)),
                      ["Host2", "Host1"])

    # Get() returns the most recent version.
    self.assertEquals(client.Get(client.Schema.HOSTNAME), "Host2")

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
        with aff4.FACTORY.OpenWithLock(self.client_id, token=self.token,
                                       blocking=True, blocking_lock_timeout=1):
          pass

      self.assertRaises(aff4.LockError, TryOpen)

  def testLockHasLimitedLeaseTime(self):
    original_time = time.time
    try:
      time.time = lambda: 100

      client = aff4.FACTORY.Create(self.client_id, "VFSGRRClient", mode="w",
                                   token=self.token)
      client.Set(client.Schema.HOSTNAME("client1"))
      client.Close()

      lock_error_catched = False
      try:
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
          # Now disable the lock so the implicit close call does not raise.
          fd._locked = False

      except aff4.LockError:
        # We expect a lock error here, because it's raised when Close() is
        # called after the lease has expired.
        lock_error_catched = True

      self.assertTrue(lock_error_catched)

    finally:
      time.time = original_time

  def testUpdateLeaseRaisesIfObjectIsNotLocked(self):
    client = aff4.FACTORY.Create(self.client_id, "VFSGRRClient", mode="w",
                                 token=self.token)
    client.Set(client.Schema.HOSTNAME("client1"))
    client.Close()

    client = aff4.FACTORY.Open(self.client_id, token=self.token)
    self.assertRaises(aff4.LockError, client.UpdateLease, 100)

  def testUpdateLeaseRaisesIfLeaseHasExpired(self):
    original_time = time.time
    try:
      time.time = lambda: 100

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

    finally:
      time.time = original_time

  def testUpdateLeaseWorksCorrectly(self):
    original_time = time.time
    try:
      time.time = lambda: 100

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

    finally:
      time.time = original_time

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

  def CreateAndOpenObjectAndSymlink(self):
    fd_urn = rdfvalue.RDFURN("aff4:/C.0000000000000001")
    symlink_urn = rdfvalue.RDFURN("aff4:/symlink")

    fd = aff4.FACTORY.Create(fd_urn, "AFF4SymlinkTestSubject",
                             token=self.token)
    fd.Set(fd.Schema.SOME_STRING, rdfvalue.RDFString("the_string"))
    fd.Close()

    symlink = aff4.FACTORY.Create(symlink_urn, "AFF4Symlink",
                                  token=self.token)
    symlink.Set(symlink.Schema.SYMLINK_TARGET, fd_urn)
    symlink.Close()

    fd = aff4.FACTORY.Open(fd_urn, token=self.token)
    symlink = aff4.FACTORY.Open(symlink_urn, token=self.token)

    return (fd, symlink)

  def testOpenedSymlinkUrnIsEqualToTargetUrn(self):
    fd, symlink_obj = self.CreateAndOpenObjectAndSymlink()

    self.assertEqual(symlink_obj.urn, fd.urn)

  def testOpenedSymlinkAFF4AttributesAreEqualToTarget(self):
    fd, symlink_obj = self.CreateAndOpenObjectAndSymlink()

    for attr in fd.Schema.ListAttributes():
      self.assertEqual(symlink_obj.Get(attr), fd.Get(attr))


class ForemanTests(test_lib.AFF4ObjectTest):
  """Tests the Foreman."""

  clients_launched = []

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

    old_start_flow = flow.GRRFlow.StartFlow
    # Mock the StartFlow
    flow.GRRFlow.StartFlow = self.StartFlow
    try:
      # Now setup the filters
      now = time.time() * 1e6
      expires = (time.time() + 3600) * 1e6
      foreman = aff4.FACTORY.Open("aff4:/foreman", mode="rw", token=self.token)

      # Make a new rule
      rule = rdfvalue.ForemanRule(created=int(now), expires=int(expires),
                                  description="Test rule")

      # Matches Windows boxes
      rule.regex_rules.Append(attribute_name=fd.Schema.SYSTEM.name,
                              attribute_regex="Windows")

      # Will run Test Flow
      rule.actions.Append(flow_name="Test Flow",
                          argv=rdfvalue.Dict(foo="bar"))

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
                       rdfvalue.ClientURN("C.0000000000000001"))
      self.assertEqual(self.clients_launched[1][0],
                       rdfvalue.ClientURN("C.0000000000000003"))

      self.clients_launched = []

      # Run again - This should not fire since it did already
      foreman.AssignTasksToClient("C.0000000000000001")
      foreman.AssignTasksToClient("C.0000000000000002")
      foreman.AssignTasksToClient("C.0000000000000003")

      self.assertEqual(len(self.clients_launched), 0)
    finally:
      flow.GRRFlow.StartFlow = old_start_flow

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
    fd.Set(fd.Schema.INSTALL_DATE(1336480583077736 - 7*24*3600*1e6))
    fd.Close()

    fd = aff4.FACTORY.Create("C.0000000000000014", "VFSGRRClient",
                             token=self.token)
    fd.Set(fd.Schema.SYSTEM, rdfvalue.RDFString("Windows 7"))
    fd.Set(fd.Schema.LAST_BOOT_TIME(1336300000000000))
    fd.Close()

    # Mock the StartFlow
    old_start_flow = flow.GRRFlow.StartFlow
    flow.GRRFlow.StartFlow = self.StartFlow

    try:

      # Now setup the filters
      now = time.time() * 1e6
      expires = (time.time() + 3600) * 1e6
      foreman = aff4.FACTORY.Open("aff4:/foreman", mode="rw", token=self.token)

      # Make a new rule
      rule = rdfvalue.ForemanRule(created=int(now), expires=int(expires),
                                  description="Test rule(old)")

      # Matches the old client
      rule.integer_rules.Append(
          attribute_name=fd.Schema.INSTALL_DATE.name,
          operator=rdfvalue.ForemanAttributeInteger.Operator.LESS_THAN,
          value=int(1336480583077736-3600*1e6))

      old_flow = "Test flow for old clients"
      # Will run Test Flow
      rule.actions.Append(flow_name=old_flow,
                          argv=rdfvalue.Dict(dict(foo="bar")))

      # Clear the rule set and add the new rule to it.
      rule_set = foreman.Schema.RULES()
      rule_set.Append(rule)

      # Make a new rule
      rule = rdfvalue.ForemanRule(created=int(now), expires=int(expires),
                                  description="Test rule(new)")

      # Matches the newer clients
      rule.integer_rules.Append(
          attribute_name=fd.Schema.INSTALL_DATE.name,
          operator=rdfvalue.ForemanAttributeInteger.Operator.GREATER_THAN,
          value=int(1336480583077736-3600*1e6))

      new_flow = "Test flow for newer clients"

      # Will run Test Flow
      rule.actions.Append(flow_name=new_flow,
                          argv=rdfvalue.Dict(dict(foo="bar")))

      rule_set.Append(rule)

      # Make a new rule
      rule = rdfvalue.ForemanRule(created=int(now), expires=int(expires),
                                  description="Test rule(eq)")

      # Note that this also tests the handling of nonexistent attributes.
      rule.integer_rules.Append(
          attribute_name=fd.Schema.LAST_BOOT_TIME.name,
          operator=rdfvalue.ForemanAttributeInteger.Operator.EQUAL,
          value=1336300000000000)

      eq_flow = "Test flow for LAST_BOOT_TIME"

      rule.actions.Append(flow_name=eq_flow,
                          argv=rdfvalue.Dict(dict(foo="bar")))

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
                       rdfvalue.ClientURN("C.0000000000000011"))
      self.assertEqual(self.clients_launched[0][1], new_flow)
      self.assertEqual(self.clients_launched[1][0],
                       rdfvalue.ClientURN("C.0000000000000012"))
      self.assertEqual(self.clients_launched[1][1], new_flow)
      self.assertEqual(self.clients_launched[2][0],
                       rdfvalue.ClientURN("C.0000000000000013"))
      self.assertEqual(self.clients_launched[2][1], old_flow)
      self.assertEqual(self.clients_launched[3][0],
                       rdfvalue.ClientURN("C.0000000000000014"))
      self.assertEqual(self.clients_launched[3][1], eq_flow)

    finally:
      flow.GRRFlow.StartFlow = old_start_flow

  def MockTime(self):
    return self.mock_time

  def testRuleExpiration(self):

    old_time = time.time
    self.mock_time = 1000
    time.time = self.MockTime

    try:
      foreman = aff4.FACTORY.Open("aff4:/foreman", mode="rw", token=self.token)

      rules = []
      rules.append(rdfvalue.ForemanRule(created=1000 * 1000000,
                                        expires=1500 * 1000000,
                                        description="Test rule1"))
      rules.append(rdfvalue.ForemanRule(created=1000 * 1000000,
                                        expires=1200 * 1000000,
                                        description="Test rule2"))
      rules.append(rdfvalue.ForemanRule(created=1000 * 1000000,
                                        expires=1500 * 1000000,
                                        description="Test rule3"))
      rules.append(rdfvalue.ForemanRule(created=1000 * 1000000,
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
        self.mock_time = now
        fd.Set(fd.Schema.LAST_FOREMAN_TIME(100))
        fd.Flush()
        foreman = aff4.FACTORY.Open("aff4:/foreman", mode="rw",
                                    token=self.token)
        foreman.AssignTasksToClient(client_id)
        rules = foreman.Get(foreman.Schema.RULES)
        self.assertEqual(len(rules), num_rules)

    finally:
      foreman = aff4.FACTORY.Open("aff4:/foreman", mode="rw", token=self.token)
      foreman.Set(foreman.Schema.RULES())
      foreman.Close()

      time.time = old_time


class AFF4TestLoader(test_lib.GRRTestLoader):
  base_class = test_lib.AFF4ObjectTest


def main(argv):
  # Run the full test suite
  test_lib.GrrTestProgram(argv=argv, testLoader=AFF4TestLoader())

if __name__ == "__main__":
  flags.StartMain(main)
