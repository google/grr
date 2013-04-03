#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

"""Test RDFStruct implementations."""



from grr.lib import rdfvalue
from grr.lib import type_info
from grr.lib.rdfvalues import structs
from grr.lib.rdfvalues import structs_parser
from grr.lib.rdfvalues import test_base


class TestStruct(structs.RDFProtoStruct):
  """A test struct object."""

  type_infos = type_info.TypeDescriptorSet(
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
  type_infos = type_info.TypeDescriptorSet(
      type_info.ProtoUnsignedInteger(name="int", field_number=2),
      )


class ProtoInitializedTest(structs.RDFProtoStruct):
  """An RDFStruct class initialized from a .proto file."""

  # This will be used to initialize this class. Only the message with the same
  # name as this class will be parsed.
  definition = """
message ProtoInitializedTest {
  // An integer field.
  optional uint64 foo = 1;

  // A string with defaults.
  optional string name = 2 [default = "Hello"];
};

message IgnoredMessage {
  optional uint64 baz = 1;
};
"""


class RDFStructsTest(test_base.RDFValueTestCase):
  """Test the RDFStruct implementation."""

  rdfvalue_class = TestStruct

  def GenerateSample(self, number=1):
    return self.rdfvalue_class(int=number, foobar="foo%s" % number,
                               urn="http://www.example.com")

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

    tested.repeat_nested.Append(foobar="Nest1")
    tested.repeat_nested.Append(foobar="Nest2")

    data = tested.SerializeToString()

    new_tested = TestStruct()
    new_tested.ParseFromString(data)

    tested._serializer = structs.JsonSerlializer()
    new_tested._serializer = structs.JsonSerlializer()
    print new_tested.SerializeToString()
    print tested.SerializeToString()

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

  def testProtoDefinitionParser(self):
    """Test that RDFStruct can be initialized from a .proto file."""
    data = """
message ProtoTestStruct {

  // A string value
  optional string foobar = 1;

  // An integer value
  optional uint64 int = 2;
  optional ProtoTestStruct nested = 4;

  // An arbitrary RDFValue field.
  optional bytes urn = 6;

  // An enum field
  enum Type {
    FIRST = 1;
    SECOND = 2;
    THIRD = 3;
  }
  optional Type type = 7;
}
"""

    proto_test_struct_cls = structs_parser.ParseFromProto(data)[0]

    # The new class auto-registers by itself.
    self.assertEqual(proto_test_struct_cls, rdfvalue.ProtoTestStruct)

    # Parsing the new class should produce identical proto serialization other
    # than whitespace.
    self.assertEqual(proto_test_struct_cls.EmitProto().strip(),
                     data.strip())

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

  def testProtoParsedRDFStruct(self):
    """Test that we can create an RDFProtoStruct from a proto file."""
    tested = ProtoInitializedTest(foo=5)
    self.assertEqual(tested.name, "Hello")
    self.assertEqual(tested.foo, 5)

    # baz is not a known field because its in the IgnoredMessage.
    self.assertRaises(AttributeError, ProtoInitializedTest, baz=2)
