#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Test RDFStruct implementations."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import random

from builtins import range  # pylint: disable=redefined-builtin

from google.protobuf import descriptor_pool
from google.protobuf import message_factory

from grr_response_core.lib import flags
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import type_info
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.lib.rdfvalues import test_base as rdf_test_base
from grr_response_core.lib.util import compatibility
from grr.test_lib import test_lib

# pylint: mode=test


class TestStructWithManyFields(rdf_structs.RDFProtoStruct):
  """A test struct object."""

  type_description = type_info.TypeDescriptorSet(*[
      rdf_structs.ProtoString(
          name="foobar_%d" % i,
          field_number=i + 1,
          default="string",
          description="A string value",
      ) for i in range(100)
  ])


class TestStruct(rdf_structs.RDFProtoStruct):
  """A test struct object."""

  type_description = type_info.TypeDescriptorSet(
      rdf_structs.ProtoString(
          name="foobar",
          field_number=1,
          default="string",
          description="A string value",
          labels=[rdf_structs.SemanticDescriptor.Labels.HIDDEN]),
      rdf_structs.ProtoUnsignedInteger(
          name="int", field_number=2, default=5,
          description="An integer value"),
      rdf_structs.ProtoList(
          rdf_structs.ProtoString(
              name="repeated",
              field_number=3,
              description="A repeated string value")),

      # We can serialize an arbitrary RDFValue. This will be serialized into a
      # binary string and parsed on demand.
      rdf_structs.ProtoRDFValue(
          name="urn",
          field_number=6,
          default=rdfvalue.RDFURN("www.google.com"),
          rdf_type="RDFURN",
          description="An arbitrary RDFValue field."),
      rdf_structs.ProtoEnum(
          name="type",
          field_number=7,
          enum_name="Type",
          enum={
              "FIRST": 1,
              "SECOND": 2,
              "THIRD": 3
          },
          default=3,
          description="An enum field"),
      rdf_structs.ProtoFloat(
          name="float",
          field_number=8,
          description="A float number",
          default=1.1),
  )


# In order to define a recursive structure we must add it manually after the
# class definition.
TestStruct.AddDescriptor(
    rdf_structs.ProtoEmbedded(name="nested", field_number=4,
                              nested=TestStruct),)

TestStruct.AddDescriptor(
    rdf_structs.ProtoList(
        rdf_structs.ProtoEmbedded(
            name="repeat_nested", field_number=5, nested=TestStruct)),)


class PartialTest1(rdf_structs.RDFProtoStruct):
  """This is a protobuf with fewer fields than TestStruct."""
  type_description = type_info.TypeDescriptorSet(
      rdf_structs.ProtoUnsignedInteger(name="int", field_number=2),)


class DynamicTypeTest(rdf_structs.RDFProtoStruct):
  """A protobuf with dynamic types."""

  type_description = type_info.TypeDescriptorSet(
      rdf_structs.ProtoString(
          name="type",
          field_number=1,
          # By default return the TestStruct proto.
          default="TestStruct",
          description="A string value"),
      rdf_structs.ProtoDynamicEmbedded(
          name="dynamic",
          # The callback here returns the type specified by the type member.
          dynamic_cb=lambda x: rdf_structs.RDFProtoStruct.classes.get(x.type),
          field_number=2,
          description="A dynamic value based on another field."),
      rdf_structs.ProtoEmbedded(
          name="nested", field_number=3, nested=rdf_client.User))


class DynamicAnyValueTypeTest(rdf_structs.RDFProtoStruct):
  """A protobuf with dynamic types stored in AnyValue messages."""

  type_description = type_info.TypeDescriptorSet(
      rdf_structs.ProtoString(
          name="type",
          field_number=1,
          # By default return the TestStruct proto.
          description="A string value"),
      rdf_structs.ProtoDynamicAnyValueEmbedded(
          name="dynamic",
          # The callback here returns the type specified by the type member.
          dynamic_cb=lambda x: rdf_structs.RDFProtoStruct.classes.get(x.type),
          field_number=2,
          description="A dynamic value based on another field."),
  )


class AnyValueWithoutTypeFunctionTest(rdf_structs.RDFProtoStruct):
  """A protobuf with dynamic types stored in AnyValue messages."""

  type_description = type_info.TypeDescriptorSet(
      rdf_structs.ProtoDynamicAnyValueEmbedded(
          name="dynamic", field_number=1, description="A dynamic value."),)


class LateBindingTest(rdf_structs.RDFProtoStruct):
  type_description = type_info.TypeDescriptorSet(
      # A nested protobuf referring to an undefined type.
      rdf_structs.ProtoEmbedded(
          name="nested", field_number=1, nested="UndefinedYet"),
      rdf_structs.ProtoRDFValue(
          name="rdfvalue",
          field_number=6,
          rdf_type="UndefinedRDFValue",
          description="An undefined RDFValue field."),

      # A repeated late bound field.
      rdf_structs.ProtoList(
          rdf_structs.ProtoRDFValue(
              name="repeated",
              field_number=7,
              rdf_type="UndefinedRDFValue2",
              description="An undefined RDFValue field.")),
  )


class UnionTest(rdf_structs.RDFProtoStruct):
  union_field = "struct_flavor"

  type_description = type_info.TypeDescriptorSet(
      rdf_structs.ProtoEnum(
          name="struct_flavor",
          field_number=1,
          enum_name="Type",
          enum={
              "FIRST": 1,
              "SECOND": 2,
              "THIRD": 3
          },
          default=3,
          description="An union enum field"),
      rdf_structs.ProtoFloat(
          name="first",
          field_number=2,
          description="A float number",
          default=1.1),
      rdf_structs.ProtoString(
          name="second",
          field_number=3,
          default="string",
          description="A string value"),
      rdf_structs.ProtoUnsignedInteger(
          name="third",
          field_number=4,
          default=5,
          description="An integer value"),
  )


class RDFStructsTest(rdf_test_base.RDFValueTestMixin, test_lib.GRRBaseTest):
  """Test the RDFStruct implementation."""

  rdfvalue_class = TestStruct

  def GenerateSample(self, number=1):
    return self.rdfvalue_class(
        int=number,
        foobar="foo%s" % number,
        urn="www.example.com",
        float=2.3 + number)

  def testDynamicType(self):
    test_pb = DynamicTypeTest()
    # We can not assign arbitrary values to the dynamic field.
    self.assertRaises(ValueError, setattr, test_pb, "dynamic", "hello")

    # Can assign a nested field.
    test_pb.dynamic.foobar = "Hello"
    self.assertIsInstance(test_pb.dynamic, TestStruct)

    # Test serialization/deserialization.
    serialized = test_pb.SerializeToString()
    self.assertEqual(DynamicTypeTest.FromSerializedString(serialized), test_pb)

    # Test proto definition.
    self.assertEqual(
        DynamicTypeTest.EmitProto(), "message DynamicTypeTest {\n\n  "
        "// A string value\n  optional string type = 1 "
        "[default = u'TestStruct'];\n\n  "
        "// A dynamic value based on another field.\n  "
        "optional bytes dynamic = 2;\n  "
        "optional User nested = 3;\n}\n")

  def testAnyValueWithoutTypeCallback(self):
    test_pb = AnyValueWithoutTypeFunctionTest()

    for value_to_assign in [
        rdfvalue.RDFString("test"),
        rdfvalue.RDFInteger(1234),
        rdfvalue.RDFBytes(b"abc"),
        rdf_flows.GrrStatus(status="WORKER_STUCK", error_message="stuck")
    ]:
      test_pb.dynamic = value_to_assign
      serialized = test_pb.SerializeToString()
      self.assertEqual(
          AnyValueWithoutTypeFunctionTest.FromSerializedString(serialized),
          test_pb)

  def testDynamicAnyValueType(self):
    test_pb = DynamicAnyValueTypeTest(type="TestStruct")
    # We can not assign arbitrary values to the dynamic field.
    self.assertRaises(ValueError, setattr, test_pb, "dynamic", "hello")

    # Can assign a nested field.
    test_pb.dynamic.foobar = "Hello"
    self.assertIsInstance(test_pb.dynamic, TestStruct)

    # Test serialization/deserialization.
    serialized = test_pb.SerializeToString()
    self.assertEqual(
        DynamicAnyValueTypeTest.FromSerializedString(serialized), test_pb)

    # Test proto definition.
    self.assertEqual(
        DynamicAnyValueTypeTest.EmitProto(),
        "message DynamicAnyValueTypeTest {\n\n  "
        "// A string value\n  optional string type = 1;\n\n  "
        "// A dynamic value based on another field.\n  "
        "optional google.protobuf.Any dynamic = 2;\n}\n")

  def testDynamicAnyValueTypeWithPrimitiveValues(self):
    test_pb = DynamicAnyValueTypeTest(type="RDFString")
    # We can not assign arbitrary values to the dynamic field.
    self.assertRaises(ValueError, setattr, test_pb, "dynamic", 42)

    # Can assign a nested field.
    test_pb.dynamic = rdfvalue.RDFString("Hello")
    self.assertIsInstance(test_pb.dynamic, rdfvalue.RDFString)

    # Test serialization/deserialization.
    serialized = test_pb.SerializeToString()
    unserialized = DynamicAnyValueTypeTest.FromSerializedString(serialized)
    self.assertEqual(unserialized, test_pb)
    self.assertEqual(unserialized.dynamic, "Hello")

  def testProtoFileDescriptorIsGeneratedForDynamicType(self):
    test_pb_file_descriptor, deps = DynamicTypeTest.EmitProtoFileDescriptor(
        "grr_export")

    pool = descriptor_pool.DescriptorPool()
    for file_descriptor in deps + [test_pb_file_descriptor]:
      pool.Add(file_descriptor)

    proto_descriptor = pool.FindMessageTypeByName("grr_export.DynamicTypeTest")
    factory = message_factory.MessageFactory()
    proto_class = factory.GetPrototype(proto_descriptor)

    # Now let's define an RDFProtoStruct for the dynamically generated
    # proto_class.
    new_dynamic_class = compatibility.MakeType(
        "DynamicTypeTestReversed", (rdf_structs.RDFProtoStruct,),
        dict(protobuf=proto_class, rdf_deps=[rdf_client.User]))
    new_dynamic_instance = new_dynamic_class(
        type="foo", nested=rdf_client.User(username="bar"))
    self.assertEqual(new_dynamic_instance.type, "foo")
    self.assertEqual(new_dynamic_instance.nested.username, "bar")

  def testProtoFileDescriptorIsGeneratedForDynamicAnyValueType(self):
    test_pb_file_descriptor, deps = (
        DynamicAnyValueTypeTest.EmitProtoFileDescriptor("grr_export"))

    pool = descriptor_pool.DescriptorPool()
    for file_descriptor in deps + [test_pb_file_descriptor]:
      pool.Add(file_descriptor)
    proto_descriptor = pool.FindMessageTypeByName(
        "grr_export.DynamicAnyValueTypeTest")
    factory = message_factory.MessageFactory()
    proto_class = factory.GetPrototype(proto_descriptor)

    # Now let's define an RDFProtoStruct for the dynamically generated
    # proto_class.
    new_dynamic_class = compatibility.MakeType(
        "DynamicAnyValueTypeTestReversed",
        (rdf_structs.RDFProtoStruct,),
        dict(protobuf=proto_class),
    )
    new_dynamic_instance = new_dynamic_class(type="foo")
    self.assertEqual(new_dynamic_instance.type, "foo")

    # Test that a proto can be deserialized from serialized RDFValue
    # with a dynamic AnyValue field.
    test_pb = DynamicAnyValueTypeTest(type="TestStruct")
    test_pb.dynamic.foobar = "Hello"

    proto_value = proto_class()
    proto_value.ParseFromString(test_pb.SerializeToString())

    self.assertEqual(proto_value.type, "TestStruct")
    self.assertEqual(proto_value.dynamic.type_url, "TestStruct")
    self.assertEqual(proto_value.dynamic.value,
                     test_pb.dynamic.SerializeToString())

  def testStructDefinition(self):
    """Ensure that errors in struct definitions are raised."""
    # A descriptor without a field number should raise.
    self.assertRaises(
        type_info.TypeValueError, rdf_structs.ProtoEmbedded, name="name")

    # Adding a duplicate field number should raise.
    self.assertRaises(
        type_info.TypeValueError, TestStruct.AddDescriptor,
        rdf_structs.ProtoUnsignedInteger(name="int", field_number=2))

    # Adding a descriptor which is not a Proto* descriptor is not allowed for
    # Struct fields:
    self.assertRaises(type_info.TypeValueError, TestStruct.AddDescriptor,
                      type_info.String(name="int"))

  def testRepeatedMember(self):
    tested = TestStruct(int=5)
    tested.foobar = "Hello"
    tested.repeated.Append("Good")
    tested.repeated.Append("Bye")

    for i in range(10):
      tested.repeat_nested.Append(foobar="Nest%s" % i)

    data = tested.SerializeToString()

    # Parse it again.
    new_tested = TestStruct.FromSerializedString(data)

    # Test the repeated field.
    self.assertLen(new_tested.repeat_nested, 10)
    self.assertEqual(new_tested.repeat_nested[1].foobar, "Nest1")

    # Check that slicing works.
    sliced = new_tested.repeat_nested[3:5]
    self.assertEqual(sliced.__class__, new_tested.repeat_nested.__class__)
    self.assertEqual(sliced.type_descriptor,
                     new_tested.repeat_nested.type_descriptor)

    self.assertLen(sliced, 2)
    self.assertEqual(sliced[0].foobar, "Nest3")

  def testUnknownFields(self):
    """Test that unknown fields are preserved across decode/encode cycle."""
    tested = TestStruct(foobar="hello", int=5)
    tested.nested.foobar = "goodbye"

    self.assertEqual(tested.foobar, "hello")
    self.assertEqual(tested.nested.foobar, "goodbye")

    data = tested.SerializeToString()

    # Now unpack using a protobuf with less fields defined.
    reduced_tested = PartialTest1.FromSerializedString(data)

    self.assertEqual(reduced_tested.int, 5)
    self.assertRaises(AttributeError, getattr, reduced_tested, "foobar")

    # Re-Serialize using the simple protobuf.
    data2 = reduced_tested.SerializeToString()
    decoded_tested = TestStruct.FromSerializedString(data2)

    # The foobar field should have been preserved, despite PartialTest1() not
    # understanding it.
    self.assertEqual(decoded_tested.foobar, "hello")

    # Check that nested fields are also preserved.
    self.assertEqual(decoded_tested.nested.foobar, "goodbye")

  def testRDFStruct(self):
    tested = TestStruct()

    # cant set integers for string attributes.
    self.assertRaises(type_info.TypeValueError, setattr, tested, "foobar", 1)

    # This is a string so a string assignment is good:
    tested.foobar = "Hello"
    self.assertEqual(tested.foobar, "Hello")

    # This field must be another TestStruct instance..
    self.assertRaises(ValueError, setattr, tested, "nested", "foo")

    # Its ok to assign a compatible semantic protobuf.
    tested.nested = TestStruct(foobar="nested_foo")

    # Not OK to use the wrong semantic type.
    self.assertRaises(ValueError, setattr, tested, "nested",
                      PartialTest1(int=1))

    # Not OK to assign a serialized string - even if it is for the right type -
    # since there is no type checking.
    serialized = TestStruct(foobar="nested_foo").SerializeToString()
    self.assertRaises(ValueError, setattr, tested, "nested", serialized)

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
    tested.urn = "www.example.com"
    self.assertIsInstance(tested.urn, rdfvalue.RDFURN)

    self.assertEqual(tested.urn, rdfvalue.RDFURN("www.example.com"))

    # Test enums.
    self.assertEqual(tested.type, 3)
    self.assertEqual(tested.type.name, "THIRD")

    tested.type = "FIRST"
    self.assertEqual(tested.type, 1)

    # Check that string assignments are case-insensitive.
    tested.type = "second"
    self.assertEqual(tested.type, 2)
    tested.type = "ThIrD"
    self.assertEqual(tested.type, 3)

    # Non-valid types are rejected.
    self.assertRaises(type_info.TypeValueError, setattr, tested, "type", "Foo")

    # Strings of digits should be accepted.
    tested.type = "2"
    self.assertEqual(tested.type, 2)
    # unicode strings should be treated the same way.
    tested.type = u"2"
    self.assertEqual(tested.type, 2)
    # Out of range values are permitted and preserved through serialization.
    tested.type = 4
    self.assertEqual(tested.type, 4)
    serialized_type = str(tested.type)
    tested.type = 1
    tested.type = serialized_type
    self.assertEqual(tested.type, 4)

  def testCacheInvalidation(self):
    path = rdf_paths.PathSpec(path="/", pathtype=rdf_paths.PathSpec.PathType.OS)
    for x in "01234":
      path.last.Append(path=x, pathtype=rdf_paths.PathSpec.PathType.OS)

    serialized = path.SerializeToString()

    path = rdf_paths.PathSpec.FromSerializedString(serialized)

    # At this point the wire format cache is fully populated (since the proto
    # had been parsed). We change a deeply nested member.
    path.last.path = "booo"

    # When we serialize the modified proto we should get the new field
    # serialized. If the cache is not properly invalidated, we will return the
    # old result instead.
    self.assertIn("booo", path.SerializeToString())

  def testLateBinding(self):
    # The LateBindingTest protobuf is not fully defined.
    self.assertRaises(KeyError, LateBindingTest.type_infos.__getitem__,
                      "nested")

    self.assertIn("UndefinedYet", rdfvalue._LATE_BINDING_STORE)

    # We can still use this protobuf
    tested = LateBindingTest()

    # But it does not know about the field yet.
    self.assertRaises(AttributeError, tested.Get, "nested")
    self.assertRaises(AttributeError, LateBindingTest, nested=None)

    # Now define the class. This should resolve the late bound fields and re-add
    # them to their owner protobufs.
    class UndefinedYet(rdf_structs.RDFProtoStruct):
      type_description = type_info.TypeDescriptorSet(
          rdf_structs.ProtoString(
              name="foobar", field_number=1, description="A string value"),)

    # The field is now resolved.
    self.assertNotIn("UndefinedYet", rdfvalue._LATE_BINDING_STORE)
    nested_field = LateBindingTest.type_infos["nested"]
    self.assertEqual(nested_field.name, "nested")

    # We can now use the protobuf as normal.
    tested = LateBindingTest()
    tested.nested.foobar = "foobar string"
    self.assertIsInstance(tested.nested, UndefinedYet)

  def testRDFValueLateBinding(self):
    # The LateBindingTest protobuf is not fully defined.
    self.assertRaises(KeyError, LateBindingTest.type_infos.__getitem__,
                      "rdfvalue")

    self.assertIn("UndefinedRDFValue", rdfvalue._LATE_BINDING_STORE)

    # We can still use this protobuf
    tested = LateBindingTest()

    # But it does not know about the field yet.
    self.assertRaises(AttributeError, tested.Get, "rdfvalue")
    self.assertRaises(AttributeError, LateBindingTest, rdfvalue="foo")

    # Now define the class. This should resolve the late bound fields and re-add
    # them to their owner protobufs.
    class UndefinedRDFValue(rdfvalue.RDFString):
      pass

    # The field is now resolved.
    self.assertNotIn("UndefinedRDFValue", rdfvalue._LATE_BINDING_STORE)
    rdfvalue_field = LateBindingTest.type_infos["rdfvalue"]
    self.assertEqual(rdfvalue_field.name, "rdfvalue")

    # We can now use the protobuf as normal.
    tested = LateBindingTest(rdfvalue="foo")
    self.assertEqual(type(tested.rdfvalue), UndefinedRDFValue)

  def testRepeatedRDFValueLateBinding(self):
    # The LateBindingTest protobuf is not fully defined.
    self.assertRaises(KeyError, LateBindingTest.type_infos.__getitem__,
                      "repeated")

    self.assertIn("UndefinedRDFValue2", rdfvalue._LATE_BINDING_STORE)

    # We can still use this protobuf
    tested = LateBindingTest()

    # But it does not know about the field yet.
    self.assertRaises(AttributeError, tested.Get, "repeated")
    self.assertRaises(AttributeError, LateBindingTest, repeated=["foo"])

    # Now define the class. This should resolve the late bound fields and re-add
    # them to their owner protobufs.
    class UndefinedRDFValue2(rdfvalue.RDFString):
      pass

    # The field is now resolved.
    self.assertNotIn("UndefinedRDFValue2", rdfvalue._LATE_BINDING_STORE)
    rdfvalue_field = LateBindingTest.type_infos["repeated"]
    self.assertEqual(rdfvalue_field.name, "repeated")

    # We can now use the protobuf as normal.
    tested = LateBindingTest(repeated=["foo"])
    self.assertLen(tested.repeated, 1)
    self.assertEqual(tested.repeated[0], "foo")
    self.assertEqual(type(tested.repeated[0]), UndefinedRDFValue2)

  def testRDFValueParsing(self):
    stat = rdf_client_fs.StatEntry.protobuf(st_mode=16877)
    data = stat.SerializeToString()

    result = rdf_client_fs.StatEntry.FromSerializedString(data)

    self.assertIsInstance(result.st_mode, rdf_client_fs.StatMode)

  def testDefaults(self):
    """Accessing a field which does not exist returns a default."""
    # An empty protobuf.
    tested = TestStruct()

    # Simple strings.
    self.assertFalse(tested.HasField("foobar"))
    self.assertEqual(tested.foobar, "string")
    self.assertFalse(tested.HasField("foobar"))

    # RDFValues.
    self.assertFalse(tested.HasField("urn"))
    self.assertEqual(tested.urn, "www.google.com")
    self.assertFalse(tested.HasField("urn"))

    # Nested fields: Accessing a nested field will create the nested protobuf.
    self.assertFalse(tested.HasField("nested"))
    self.assertEqual(tested.nested.urn, "www.google.com")
    self.assertTrue(tested.HasField("nested"))
    self.assertFalse(tested.nested.HasField("urn"))

  def testUnionCast(self):
    """Check union structs handling."""
    # An empty protobuf.
    tested_non_union = TestStruct()

    # Raises if union-casting is attemted on non-union proto.
    self.assertRaises(AttributeError, tested_non_union.UnionCast)

    # A proto with a semantic union_field. In this particular proto the chosen
    # union variant is called struct_flavor, but it's arbitrary, we also use
    # eg rule_type reffering to the chosen union variant elsewhere. This is
    # determined by the value of union_field.
    tested_union = UnionTest()

    # Returns the default value of the default flavor if both struct_flavor and
    # the flavored field are not set.
    self.assertEqual(tested_union.UnionCast(), 5)

    tested_union.struct_flavor = "FIRST"
    # Returns the default value of the selected flavor if it's not been changed.
    self.assertEqual(tested_union.UnionCast(), 1.1)

    tested_union.struct_flavor = "SECOND"
    # Same as above.
    self.assertEqual(tested_union.UnionCast(), "string")

    tested_union.struct_flavor = "THIRD"
    # Once again.
    self.assertEqual(tested_union.UnionCast(), 5)

    tested_union.third = 1337
    # Returns the set flavor value.
    self.assertEqual(tested_union.UnionCast(), 1337)

    tested_union.first = 1.61803399
    # Raises if there is a flavored field set that doesn't match struct_flavor.
    self.assertRaises(ValueError, tested_union.UnionCast)

  def testClearFieldsWithLabelWorksCorrectly(self):
    t = TestStruct(foobar="foo", int=42)
    t.ClearFieldsWithLabel(rdf_structs.SemanticDescriptor.Labels.HIDDEN)
    self.assertFalse(t.HasField("foobar"))
    self.assertTrue(t.HasField("int"))

  def testClearFieldsWithLabelWorksCorrectlyOnNestedStructures(self):
    t = TestStruct(foobar="foo", int=42)
    t.nested = TestStruct(foobar="bar", int=43)
    t.ClearFieldsWithLabel(rdf_structs.SemanticDescriptor.Labels.HIDDEN)
    self.assertFalse(t.nested.HasField("foobar"))
    self.assertTrue(t.nested.HasField("int"))

  def testConversionToPrimitiveDictNoSerialization(self):
    test_struct = TestStruct(
        foobar="foo",
        int=2,
        repeated=["value0", "value1"],
        nested=TestStruct(int=567),
        repeat_nested=[TestStruct(int=568)])
    expected_dict = {
        "foobar": "foo",
        "int": 2,
        "repeated": ["value0", "value1"],
        "nested": {
            "int": 567
        },
        "repeat_nested": [{
            "int": 568
        }]
    }
    self.assertEqual(test_struct.ToPrimitiveDict(), expected_dict)

  def testConversionToPrimitiveDictWithSerialization(self):
    test_struct = TestStruct(
        foobar="foo",
        int=2,
        repeated=["value0", "value1"],
        nested=TestStruct(int=567),
        repeat_nested=[TestStruct(int=568)])
    expected_dict = {
        "foobar": "foo",
        "int": "2",  # Serialized
        "repeated": ["value0", "value1"],
        "nested": {
            "int": "567"  # Serialized
        },
        "repeat_nested": [{
            "int": "568"  # Serialized
        }]
    }
    self.assertEqual(
        test_struct.ToPrimitiveDict(serialize_leaf_fields=True), expected_dict)

  def _GenerateSampleWithManyFields(self):
    fields = {}
    for _ in range(50):
      key = "foobar_%d" % random.randrange(100)
      fields[key] = key

    sample = TestStructWithManyFields(**fields)

    parsed = TestStructWithManyFields()
    parsed.ParseFromString(sample.SerializeToString())

    return sample, parsed

  def testSerializationIsStable(self):
    sample1, sample2 = self._GenerateSampleWithManyFields()

    self.assertEqual(sample1.SerializeToString(), sample2.SerializeToString())

  def testHashingIsStable(self):
    sample1, sample2 = self._GenerateSampleWithManyFields()

    self.assertEqual(hash(sample1), hash(sample2))


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
