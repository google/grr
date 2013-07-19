#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

"""Test RDFStruct implementations."""



from grr.lib import rdfvalue
from grr.lib import type_info
from grr.lib.rdfvalues import structs
from grr.lib.rdfvalues import test_base


class TestStruct(structs.RDFProtoStruct):
  """A test struct object."""

  type_description = type_info.TypeDescriptorSet(
      type_info.ProtoString(name="foobar", field_number=1,
                            description="A string value"),

      type_info.ProtoUnsignedInteger(name="int", field_number=2,
                                     description="An integer value"),

      type_info.ProtoList(type_info.ProtoString(
          name="repeated", field_number=3,
          description="A repeated string value")),

      # We can serialize an arbitrary RDFValue. This will be serialized into a
      # binary string and parsed on demand.
      type_info.ProtoRDFValue(name="urn", field_number=6,
                              rdf_type="RDFURN",
                              description="An arbitrary RDFValue field."),

      type_info.ProtoEnum(name="type", field_number=7,
                          enum_name="Type",
                          enum=dict(FIRST=1, SECOND=2, THIRD=3),
                          description="An enum field"),

      type_info.ProtoFloat(name="float", field_number=8,
                           description="A float number", default=1.1),
      )


# In order to define a recursive structure we must add it manually after the
# class definition.
TestStruct.AddDescriptor(
    type_info.ProtoNested(
        name="nested", field_number=4,
        nested=TestStruct),
    )

TestStruct.AddDescriptor(
    type_info.ProtoList(type_info.ProtoNested(
        name="repeat_nested", field_number=5,
        nested=TestStruct)),
    )


class PartialTest1(structs.RDFProtoStruct):
  """This is a protobuf with fewer fields than TestStruct."""
  type_description = type_info.TypeDescriptorSet(
      type_info.ProtoUnsignedInteger(name="int", field_number=2),
      )


class RDFStructsTest(test_base.RDFValueTestCase):
  """Test the RDFStruct implementation."""

  rdfvalue_class = TestStruct

  def GenerateSample(self, number=1):
    return self.rdfvalue_class(int=number, foobar="foo%s" % number,
                               urn="http://www.example.com",
                               float=2.3+number)

  def testStructDefinition(self):
    """Ensure that errors in struct definitions are raised."""
    # A descriptor without a field number should raise.
    self.assertRaises(type_info.TypeValueError,
                      type_info.ProtoNested, name="name")

    # Adding a duplicate field number should raise.
    self.assertRaises(
        type_info.TypeValueError, TestStruct.AddDescriptor,
        type_info.ProtoUnsignedInteger(name="int", field_number=2))

    # Adding a descriptor which is not a Proto* descriptor is not allowed for
    # Struct fields:
    self.assertRaises(
        type_info.TypeValueError, TestStruct.AddDescriptor,
        type_info.String(name="int"))

    print TestStruct.EmitProto()

  def testRepeatedMember(self):
    tested = TestStruct(int=5)
    tested.foobar = "Hello"
    tested.repeated.Append("Good")
    tested.repeated.Append("Bye")

    for i in range(10):
      tested.repeat_nested.Append(foobar="Nest%s" % i)

    data = tested.SerializeToString()

    # Parse it again.
    new_tested = TestStruct(data)

    # Test the repeated field.
    self.assertEqual(len(new_tested.repeat_nested), 10)
    self.assertEqual(new_tested.repeat_nested[1].foobar, "Nest1")

    # Check that slicing works.
    sliced = new_tested.repeat_nested[3:5]
    self.assertEqual(sliced.__class__, new_tested.repeat_nested.__class__)
    self.assertEqual(sliced.type_descriptor,
                     new_tested.repeat_nested.type_descriptor)

    self.assertEqual(len(sliced), 2)
    self.assertEqual(sliced[0].foobar, "Nest3")

  def testUnknownFields(self):
    """Test that unknown fields are preserved across decode/encode cycle."""
    tested = TestStruct(foobar="hello", int=5)
    tested.nested.foobar = "goodbye"

    self.assertEqual(tested.foobar, "hello")
    self.assertEqual(tested.nested.foobar, "goodbye")

    data = tested.SerializeToString()

    # Now unpack using a protobuf with less fields defined.
    reduced_tested = PartialTest1(data)

    self.assertEqual(reduced_tested.int, 5)
    self.assertRaises(AttributeError, getattr, reduced_tested, "foobar")

    # Re-Serialize using the simple protobuf.
    data2 = reduced_tested.SerializeToString()
    decoded_tested = TestStruct(data2)

    # The foobar field should have been preserved, despite PartialTest1() not
    # understanding it.
    self.assertEqual(decoded_tested.foobar, "hello")

    # Check that nested fields are also preserved.
    self.assertEqual(decoded_tested.nested.foobar, "goodbye")

  def testRDFStruct(self):
    tested = TestStruct()

    # cant set integers for string attributes.
    self.assertRaises(type_info.TypeValueError, setattr,
                      tested, "foobar", 1)

    # This is a string so a string assignment is good:
    tested.foobar = "Hello"
    self.assertEqual(tested.foobar, "Hello")

    # This field must be another TestStruct instance..
    self.assertRaises(ValueError, setattr, tested, "nested", "foo")

    tested.nested = TestStruct(foobar="nested_foo")

    # Nested accessors.
    self.assertEqual(tested.nested.foobar, "nested_foo")

    # Test repeated elements:

    # Empty list is ok:
    tested.repeated = []
    self.assertEqual(tested.repeated, [])

    tested.repeated = ["string"]
    self.assertEqual(tested.repeated, ["string"])

    self.assertRaises(type_info.TypeValueError, setattr, tested, "repeated",
                      [1, 2, 3])

    # Coercing on assignment. This field is an RDFURN:
    tested.urn = "http://www.example.com"
    self.assertTrue(isinstance(tested.urn, rdfvalue.RDFURN))

    self.assertEqual(tested.urn, rdfvalue.RDFURN("http://www.example.com"))

    # Test enums.
    tested.type = "FIRST"
    self.assertEqual(tested.type, 1)

    # Non-valid types are rejected.
    self.assertRaises(type_info.TypeValueError, setattr, tested, "type", "Foo")

    print tested

  def testCacheInvalidation(self):
    path = rdfvalue.PathSpec(path="/", pathtype=rdfvalue.PathSpec.PathType.OS)
    for x in "01234":
      path.last.Append(path=x, pathtype=rdfvalue.PathSpec.PathType.OS)

    serialized = path.SerializeToString()

    path = rdfvalue.PathSpec(serialized)

    # At this point the wire format cache is fully populated (since the proto
    # had been parsed). We change a deeply nested member.
    path.last.path = "booo"

    # When we serialize the modified proto we should get the new field
    # serialized. If the cache is not properly invalidated, we will return the
    # old result instead.
    self.assertTrue("booo" in path.SerializeToString())

  def testWireFormatAccess(self):

    m = rdfvalue.SignedMessageList()

    now = 1369308998000000

    self.assertEqual(m.timestamp, 0)

    m.SetWireFormat("timestamp", now)

    self.assertTrue(isinstance(m.timestamp, rdfvalue.RDFDatetime))
    self.assertEqual(m.timestamp, now)

    rdf_now = rdfvalue.RDFDatetime().Now()

    m.timestamp = rdf_now
    self.assertEqual(m.GetWireFormat("timestamp"), int(rdf_now))
