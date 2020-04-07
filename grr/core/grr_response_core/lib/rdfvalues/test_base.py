#!/usr/bin/env python
# Lint as: python3
# -*- encoding: utf-8 -*-
"""The base classes for RDFValue tests."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from typing import Text

from grr_response_core.lib import serialization
from grr_response_core.lib.rdfvalues import structs as rdf_structs

# pylint:mode=test


class RDFValueTestMixin(object):
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

    self.assertEqual(value, sample)

  def testComparisons(self):
    """Checks that object comparisons work."""
    sample1 = self.GenerateSample(1)

    # pylint: disable=g-generic-assert
    self.assertTrue(sample1 == self.GenerateSample(1))
    self.assertFalse(sample1 == self.GenerateSample(2))
    self.assertTrue(sample1 != self.GenerateSample(2))
    self.assertFalse(sample1 != self.GenerateSample(1))
    # pylint: enable=g-generic-assert

  def testHashability(self):
    """RDFValue instances need to act as keys in a dict."""
    sample1 = self.GenerateSample(1)

    if isinstance(sample1, rdf_structs.RDFStruct):
      self.skipTest("Hashing is unsupported.")

    # Different instances with the same value need to hash to the same.
    self.assertEqual(hash(sample1), hash(self.GenerateSample(1)))
    self.assertNotEqual(hash(sample1), hash(self.GenerateSample(2)))

  def testInitialization(self):
    """Check that we can use an empty initializer.

    RDFValues are created in many different ways, sometimes in stages by
    gradually populating fields. The only time you can be sure the user has
    finished creating a proto is when it is serialized. This means strong
    validation that requires all fields populated can't be done in init, but
    should be done in SerializeToBytes.
    """
    self.rdfvalue_class()

    # Initialize from another instance.
    sample = self.GenerateSample()

    self.CheckRDFValue(self.rdfvalue_class(sample), sample)

  def testSerialization(self, sample=None):
    """Make sure the RDFValue instance can be serialized."""
    if sample is None:
      sample = self.GenerateSample()

    # Serializing to a string must produce a string.
    serialized = serialization.ToBytes(sample)
    self.assertIsInstance(serialized, bytes)

    # Ensure we can parse it again.

    rdfvalue_object = serialization.FromBytes(self.rdfvalue_class, serialized)
    self.CheckRDFValue(rdfvalue_object, sample)

    # Serializing to data store must produce something the data store can
    # handle.
    serialized = serialization.ToWireFormat(sample)
    protobuf_type = serialization.GetProtobufType(type(sample))

    if protobuf_type == "bytes":
      self.assertIsInstance(serialized, bytes)
    elif protobuf_type == "string":
      self.assertIsInstance(serialized, Text)
    elif protobuf_type in ["unsigned_integer", "integer"]:
      self.assertIsInstance(serialized, int)
    else:
      self.fail("%s has no valid protobuf_type" % self.rdfvalue_class)

    # Ensure we can parse it again.
    rdfvalue_object = serialization.FromWireFormat(self.rdfvalue_class,
                                                   serialized)
    self.CheckRDFValue(rdfvalue_object, sample)


class RDFProtoTestMixin(RDFValueTestMixin):
  """A harness for testing RDFProto implementations."""

  __abstract = True  # Do not register this class so pylint: disable=g-bad-name

  def testInitializationEx(self):
    """Check we can initialize from additional parts."""
    sample = self.GenerateSample()

    # RDFProto can be initialized from a serialized protobuf.
    serialized = sample.SerializeToBytes()
    rdfvalue_sample = self.rdfvalue_class.FromSerializedBytes(serialized)
    self.CheckRDFValue(rdfvalue_sample, sample)

    # RDFProto can be initialized from another RDFProto.
    new_rdfvalue_sample = self.rdfvalue_class(rdfvalue_sample)
    self.CheckRDFValue(new_rdfvalue_sample, rdfvalue_sample)
