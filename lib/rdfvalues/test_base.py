#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""The base classes for RDFValue tests."""
import time

from grr.lib import aff4
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib import type_info

# pylint:mode=test


class RDFValueBaseTest(test_lib.GRRBaseTest):
  pass


class GenericRDFProtoTest(RDFValueBaseTest):

  def testNestedProtobufAssignment(self):
    """Check that we can assign a nested protobuf."""
    container = rdfvalue.RekallRequest()
    pathspec = rdfvalue.PathSpec(path=r"\\.\pmem", pathtype=1)

    # Should raise - incompatible RDFType.
    self.assertRaises(
        type_info.TypeValueError,
        setattr, container, "device", rdfvalue.RDFString("hello"))

    # Should raise - incompatible RDFProto type.
    self.assertRaises(
        type_info.TypeValueError,
        setattr, container, "device", rdfvalue.StatEntry(st_size=5))

    # Assign directly.
    container.device = pathspec

    self.assertEqual(container.device.path, r"\\.\pmem")

    # Clear the field.
    container.device = None

    # Check the protobuf does not have the field set at all.
    self.assertFalse(container.HasField("device"))

  def testSimpleTypeAssignment(self):
    sample = rdfvalue.StatEntry()
    sample.AddDescriptor(type_info.ProtoRDFValue(
        name="test", field_number=45, default=rdfvalue.RDFInteger(0),
        rdf_type=rdfvalue.RDFInteger))

    # Ensure there is an rdf_map so we know that st_size is an RDFInteger:
    self.assertIsInstance(sample.test, rdfvalue.RDFInteger)

    # Can we assign an RDFValue instance?
    sample.test = rdfvalue.RDFInteger(5)

    self.assertEqual(sample.test, 5)

    # Check that bare values can be coerced.
    sample.test = 6
    self.assertIsInstance(sample.test, rdfvalue.RDFInteger)
    self.assertEqual(sample.test, 6)

    # Assign an enum.
    sample.registry_type = sample.RegistryType.REG_DWORD
    self.assertEqual(sample.registry_type, sample.RegistryType.REG_DWORD)

    sample.registry_type = rdfvalue.StatEntry.RegistryType.REG_SZ
    self.assertEqual(sample.registry_type, sample.RegistryType.REG_SZ)

    # We can also assign the string value.
    sample.registry_type = "REG_QWORD"
    self.assertEqual(sample.registry_type, sample.RegistryType.REG_QWORD)

    # Check that coercing works.
    sample.test = "10"
    self.assertEqual(sample.test, 10)

    # Assign an RDFValue which can not be coerced.
    self.assertRaises(
        type_info.TypeValueError,
        setattr, sample, "test", rdfvalue.RDFString("hello"))

  def testComplexConstruction(self):
    """Test that we can construct RDFProtos with nested fields."""
    pathspec = rdfvalue.PathSpec(path="/foobar",
                                 pathtype=rdfvalue.PathSpec.PathType.TSK)
    sample = rdfvalue.StatEntry(pathspec=pathspec,
                                st_size=5)

    self.assertEqual(sample.pathspec.path, "/foobar")
    self.assertEqual(sample.st_size, 5)

    self.assertRaises(
        AttributeError, rdfvalue.StatEntry, foobar=1)

  def testUnicodeSupport(self):
    pathspec = rdfvalue.PathSpec(path="/foobar",
                                 pathtype=rdfvalue.PathSpec.PathType.TSK)
    pathspec.path = u"Grüezi"

    self.assertEqual(pathspec.path, u"Grüezi")

  def testRDFTypes(self):
    """Test that types are properly serialized."""
    # Create an object to carry attributes
    obj = aff4.FACTORY.Create("foobar", "AFF4Object", token=self.token)

    # Make a url object
    str_url = "aff4:/users"
    url = rdfvalue.RDFURN(str_url, age=1)

    # Store it
    # We must use a proper Attribute() instance
    self.assertRaises(AttributeError, obj.Set, "aff4:stored", url)
    self.assertRaises(ValueError, obj.Set, obj.Schema.STORED, str_url)

    old_time = time.time
    try:
      time.time = lambda: 100

      obj.Set(obj.Schema.STORED, url)
      obj.Close()

      # Check that its ok
      obj = aff4.FACTORY.Open("foobar", token=self.token)
      url = obj.Get(obj.Schema.STORED)

      # It must be a real RDFURN and be the same as the original string
      self.assertEqual(url.__class__, rdfvalue.RDFURN)
      self.assertEqual(str(url), str_url)

      # The time of the stored property reflects the time of the Set() call.
      self.assertEqual(url.age, 100 * 1e6)

    finally:
      time.time = old_time

  def testRepeatedFields(self):
    """Test handling of protobuf repeated fields."""
    sample = rdfvalue.Interface()

    # Add a simple string.
    sample.ip4_addresses.Append("127.0.0.1")

    self.assertEqual(sample.ip4_addresses[0], "127.0.0.1")

    # Add an invalid type.
    self.assertRaises(type_info.TypeValueError, sample.addresses.Append, 2)

    # Add a protobuf
    sample.addresses.Append(human_readable="127.0.0.1")

    self.assertEqual(sample.addresses[0].human_readable, "127.0.0.1")
    self.assertEqual(len(sample.addresses), 1)

  def testEnums(self):
    """Check that enums are wrapped in a descriptor class."""
    sample = rdfvalue.GrrStatus()
    self.assertEqual(str(sample.status), "OK")


class RDFValueTestCase(RDFValueBaseTest):
  """The base class for testing RDFValue implementations."""

  # This should be overridden by the RDFValue class we want to test.
  rdfvalue_class = lambda *args, **kw: None

  __abstract = True  # Do not register this class so pylint: disable=g-bad-name

  def GenerateSample(self, number=0):
    """Create a pre-populated instance of the RDFValue.

    Args:
      number: A sample number. Derived classes should return a different sample
        for each number.
    """
    _ = number
    return self.rdfvalue_class()

  def CheckRDFValue(self, value, sample):
    """Check that the rdfproto is the same as the sample."""
    self.assertIsInstance(sample, self.rdfvalue_class)
    self.assertIsInstance(value, self.rdfvalue_class)

    if hasattr(value, "ListFields"):
      self.assertProtoEqual(value, sample)

  def testComparisons(self):
    """Checks that object comparisons work."""
    sample1 = self.GenerateSample(1)

    self.assertTrue(sample1 == self.GenerateSample(1))
    self.assertFalse(sample1 == self.GenerateSample(2))
    self.assertTrue(sample1 != self.GenerateSample(2))
    self.assertFalse(sample1 != self.GenerateSample(1))

  def testHashability(self):
    """RDFValue instances need to act as keys in a dict."""
    sample1 = self.GenerateSample(1)

    # Different instances with the same value need to hash to the same.
    self.assertTrue(hash(sample1) == hash(self.GenerateSample(1)))
    self.assertTrue(hash(sample1) != hash(self.GenerateSample(2)))

  def testInitialization(self):
    """Check that we can initialize from common initializers."""

    # Empty Initializer.
    self.rdfvalue_class()

    # Initialize from another instance.
    sample = self.GenerateSample()

    self.CheckRDFValue(self.rdfvalue_class(sample), sample)

  def testSerialization(self, sample=None):
    """Make sure the RDFValue instance can be serialized."""
    if sample is None:
      sample = self.GenerateSample()

    # Serializing to a string must produce a string.
    serialized = sample.SerializeToString()
    self.assertIsInstance(serialized, str)

    # Ensure we can parse it again.
    rdfvalue_object = self.rdfvalue_class(serialized)
    self.CheckRDFValue(rdfvalue_object, sample)

    # Also by initialization.
    self.CheckRDFValue(self.rdfvalue_class(serialized), sample)

    # Serializing to data store must produce something the data store can
    # handle.
    serialized = sample.SerializeToDataStore()

    if self.rdfvalue_class.data_store_type == "bytes":
      self.assertIsInstance(serialized, str)
    elif self.rdfvalue_class.data_store_type == "string":
      self.assertIsInstance(serialized, unicode)
    elif self.rdfvalue_class.data_store_type in [
        "unsigned_integer", "integer"]:
      self.assertIsInstance(serialized, (int, long))
    else:
      self.fail("%s has no valid data_store_type" % self.rdfvalue_class)

    # Ensure we can parse it again.
    rdfvalue_object = self.rdfvalue_class(serialized)
    self.CheckRDFValue(rdfvalue_object, sample)


class RDFProtoTestCase(RDFValueTestCase):
  """A harness for testing RDFProto implementations."""

  __abstract = True  # Do not register this class so pylint: disable=g-bad-name

  def CheckRDFValue(self, rdfproto, sample):
    """Check that the rdfproto is the same as the sample."""
    super(RDFProtoTestCase, self).CheckRDFValue(rdfproto, sample)
    self.assertProtoEqual(rdfproto, sample)

  def testInitializationEx(self):
    """Check we can initialize from additional parts."""
    sample = self.GenerateSample()

    # RDFProto can be initialized from a serialized protobuf.
    rdfvalue_sample = self.rdfvalue_class(sample.SerializeToString())
    self.CheckRDFValue(rdfvalue_sample, sample)

    # RDFProto can be initialized from another RDFProto.
    new_rdfvalue_sample = self.rdfvalue_class(rdfvalue_sample)
    self.CheckRDFValue(new_rdfvalue_sample, rdfvalue_sample)

    # In this case the ages should be identical
    self.assertEqual(int(new_rdfvalue_sample.age), int(rdfvalue_sample.age))
