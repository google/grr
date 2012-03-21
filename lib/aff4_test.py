#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

# Copyright 2010 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests for the flow."""

import time
from grr.client import conf
from grr.lib import aff4
from grr.lib import data_store
from grr.lib import flow
from grr.lib import test_lib
from grr.lib import utils

# Load plugins for aff4 objects and tests
from grr.lib import aff4_objects
from grr.lib.aff4_objects import tests

from grr.proto import jobs_pb2


class AFF4Tests(test_lib.AFF4ObjectTest):
  """Test the AFF4 abstraction."""

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

  def testRDFTypes(self):
    """Test that types are properly serialized."""
    # Create an object to carry attributes
    obj = aff4.FACTORY.Create("foobar", "AFF4Object", token=self.token)

    # Make a url object
    str_url = "http://www.google.com/"
    url = aff4.RDFURN(str_url, age=1)

    # Store it
    # We must use a proper Attribute() instance
    self.assertRaises(AttributeError, obj.Set, "aff4:stored", url)
    self.assertRaises(ValueError, obj.Set, obj.Schema.STORED, str_url)

    obj.Set(obj.Schema.STORED, url)
    obj.Close()

    # Check that its ok
    obj = aff4.FACTORY.Open("foobar", token=self.token)
    url = obj.Get(obj.Schema.STORED)

    # It must be a real RDFURN and be the same as the original string
    self.assertEqual(url.__class__, aff4.RDFURN)
    self.assertEqual(str(url), str_url)
    self.assertEqual(url.age, 1)

  def testRDFURN(self):
    """Test RDFURN handling."""
    # Make a url object
    str_url = "http://www.google.com/"
    url = aff4.RDFURN(str_url, age=1)
    self.assertEqual(url.age, 1)
    self.assertEqual(url.Path(), "/")
    self.assertEqual(url._urn.netloc, "www.google.com")
    self.assertEqual(url._urn.scheme, "http")

    # Test the Add() function
    url = url.Add("some", age=2).Add("path", age=3)
    self.assertEqual(url.age, 3)
    self.assertEqual(url.Path(), "/some/path")
    self.assertEqual(url._urn.netloc, "www.google.com")
    self.assertEqual(url._urn.scheme, "http")

  def testRDFProto(self):
    """Tests that the RDFProto RDFValue serialization works."""

    class RDFProtoTest(aff4.RDFProto):
      _proto = jobs_pb2.GrrMessage

    # Check that we can initialize from a serialized proto
    my_proto = jobs_pb2.GrrMessage(session_id="test1",
                                   request_id=123,
                                   args="hello",
                                   source="foobar")

    test_obj = RDFProtoTest(my_proto.SerializeToString())

    self.assertEqual(test_obj.data, my_proto)
    self.assertEqual(test_obj.data.args, "hello")

    self.assertEqual(test_obj.SerializeToString(), my_proto.SerializeToString())

    test_obj = RDFProtoTest()
    test_obj.ParseFromString(my_proto.SerializeToString())

    self.assertEqual(test_obj.data.SerializeToString(),
                     my_proto.SerializeToString())
    self.assertEqual(test_obj.data, my_proto)

  def testRDFProtoArray(self):
    """Test the RDFProtoArray serialization."""

    class RDFProtoArrayTest(aff4.RDFProtoArray):
      _proto = jobs_pb2.GrrMessage

    array = RDFProtoArrayTest()
    for i in range(10):
      my_proto = jobs_pb2.GrrMessage(session_id="test1",
                                     request_id=i,
                                     args="hello",
                                     source="foobar")

      array.Append(my_proto)

    # We do not allow non compatible objects to be added.
    self.assertRaises(TypeError, array.Append, jobs_pb2.GrrStatus())
    serialized = array.SerializeToString()

    # Now unserialize
    array = RDFProtoArrayTest(serialized)
    self.assertEqual(len(array.data), 10)
    for i, member in enumerate(array):
      self.assertEqual(i, member.request_id)

    # Explicit parsing
    array = RDFProtoArrayTest()
    array.ParseFromString(serialized)
    self.assertEqual(len(array.data), 10)
    for i, member in enumerate(array):
      self.assertEqual(i, member.request_id)

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
    self.assertRaises(IOError, aff4.FACTORY.RDFValue("RDFX509Cert"), "My cert")

    fd.Close()

  def testAFF4Image(self):
    """Test the AFF4Image object."""
    path = "/C.12345/foo"

    fd = aff4.FACTORY.Create(path, "AFF4Image", token=self.token)
    fd.Set(fd.Schema.CHUNKSIZE(10))

    # Make lots of small writes - The length of this string and the chunk size
    # are relative primes for worst case.
    for i in range(100):
      fd.Write("Test%08X\n" % i)

    fd.Close()

    fd = aff4.FACTORY.Open(path, token=self.token)
    for i in range(100):
      self.assertEqual(fd.Read(13), "Test%08X\n" % i)

  def testAFF4FlowObject(self):
    """Test the AFF4 Flow switch and object."""
    client = aff4.FACTORY.Create(self.client_id, "VFSGRRClient",
                                 token=self.token)
    client.Close()

    # Start some new flows on it
    session_ids = [flow.FACTORY.StartFlow(self.client_id, "FlowOrderTest",
                                          token=self.token)
                   for _ in range(10)]

    # Try to open a single flow.
    switch = aff4.FACTORY.Create(aff4.FLOW_SWITCH_URN, "GRRFlowSwitch",
                                 mode="r", token=self.token)
    flow_obj = switch.OpenMember(session_ids[0])
    flow_pb = flow_obj.Get(flow_obj.Schema.FLOW_PB)

    self.assertEqual(flow_pb.data.name, "FlowOrderTest")
    self.assertEqual(flow_pb.data.session_id, session_ids[0])

    grr_flow_obj = flow_obj.GetFlowObj()
    self.assertEqual(grr_flow_obj.session_id, session_ids[0])
    self.assertEqual(grr_flow_obj.__class__.__name__, "FlowOrderTest")

    # Now load multiple flows at once
    client = aff4.FACTORY.Open(self.client_id, token=self.token,
                               age=aff4.ALL_TIMES)

    for f in client.GetFlows():
      del session_ids[session_ids.index(f.session_id)]

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
    matched = list(fd.Query(u"subject matches '\]\['"))
    self.assertEqual(len(matched), 1)
    self.assertEqual(utils.SmartUnicode(matched[0].urn),
                     u"aff4:/C.0000000000000000/"
                     u"fs/os/c/regex.*?][{}--")

    # Test the OpenChildren function on files that contain regex chars.
    fd = aff4.FACTORY.Open(aff4.ROOT_URN.Add(client_id).Add(
        "/fs/os/c/regex\V.*?]xx[{}--"), token=self.token)
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
        "subject matches '%s/r?bash'" % data_store.EscapeRegex(fd.urn)))
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


class ForemanTests(test_lib.GRRBaseTest):
  """Test the Foreman."""

  def testOperatingSystemSelection(self):
    """Test that we can distinguish based on operating system."""
    fd = aff4.FACTORY.Create("C.1", "VFSGRRClient", token=self.token)
    fd.Set(fd.Schema.ARCH, aff4.RDFString("Windows XP"))
    fd.Close()

    fd = aff4.FACTORY.Create("C.2", "VFSGRRClient", token=self.token)
    fd.Set(fd.Schema.ARCH, aff4.RDFString("Linux"))
    fd.Close()

    fd = aff4.FACTORY.Create("C.3", "VFSGRRClient", token=self.token)
    fd.Set(fd.Schema.ARCH, aff4.RDFString("Windows 7"))
    fd.Close()

    # Set up the filters
    clients_launched = []

    def StartFlow(client_id, flow_name, user=None, **kw):
      # Make sure the foreman is launching these
      self.assertEqual(user, "Foreman")

      # Make sure we pass the argv along
      self.assertEqual(kw["foo"], "bar")

      # Keep a record of all the clients
      clients_launched.append(client_id)
      print "%s run %s on %s with %s" % (user, flow_name, client_id, kw)

    # Mock the StartFlow
    flow.FACTORY.StartFlow = StartFlow

    # Now setup the filters
    now = time.time() * 1e6
    foreman = aff4.FACTORY.Open("aff4:/foreman", token=self.token)

    # Make a new rule
    rule = jobs_pb2.ForemanRule(created=int(now), description="Test rule")

    # Matches Windows boxes
    rule.regex_rules.add(attribute_name=fd.Schema.ARCH.name,
                         attribute_regex="Windows")

    # Will run Test Flow
    rule.actions.add(flow_name="Test Flow",
                     argv=utils.ProtoDict(dict(foo="bar")).ToProto())

    # Clear the rule set and add the new rule to it.
    rule_set = foreman.Schema.RULES()
    rule_set.Append(rule)

    # Assign it to the foreman
    foreman.Set(foreman.Schema.RULES, rule_set)
    foreman.Close()

    clients_launched = []
    foreman.AssignTasksToClient("C.1")
    foreman.AssignTasksToClient("C.2")
    foreman.AssignTasksToClient("C.3")

    # Make sure that only the windows machines ran
    self.assertEqual(len(clients_launched), 2)
    self.assertEqual(clients_launched[0], "C.1")
    self.assertEqual(clients_launched[1], "C.3")

    clients_launched = []

    # Run again - This should not fire since it did already
    foreman.AssignTasksToClient("C.1")
    foreman.AssignTasksToClient("C.2")
    foreman.AssignTasksToClient("C.3")

    self.assertEqual(len(clients_launched), 0)


class AFF4TestLoader(test_lib.GRRTestLoader):
  base_class = test_lib.AFF4ObjectTest


def main(argv):
  # Run the full test suite
  test_lib.GrrTestProgram(argv=argv, testLoader=AFF4TestLoader())

if __name__ == "__main__":
  conf.StartMain(main)
