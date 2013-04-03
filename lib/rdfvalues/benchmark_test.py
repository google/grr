#!/usr/bin/env python
"""This module tests the RDFValue implementation for performance."""


import time
import zlib

from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib import type_info
from grr.proto import jobs_pb2


class StructGrrMessage(rdfvalue.RDFProtoStruct):
  """A serialization agnostic GrrMessage."""

  type_infos = type_info.TypeDescriptorSet(
      type_info.ProtoString(
          name="session_id", field_number=1,
          description="Every Flow has a unique session id."),

      type_info.ProtoUnsignedInteger(
          name="request_id", field_number=2,
          description="This message is in response to this request number"),

      type_info.ProtoUnsignedInteger(
          name="response_id", field_number=3,
          description="Responses for each request."),

      type_info.ProtoString(
          name="name", field_number=4,
          description=("This is the name of the client action that will be "
                       "executed. It is set by the flow and is executed by "
                       "the client.")),

      type_info.ProtoBinary(
          name="args", field_number=5,
          description="This field contains an encoded rdfvalue."),

      type_info.ProtoString(
          name="source", field_number=6,
          description=("Client name where the message came from (This is "
                       "copied from the MessageList)")),
      )


class FastVolatilityValue(rdfvalue.RDFProtoStruct):
  type_infos = type_info.TypeDescriptorSet(
      type_info.ProtoString(
          name="type", field_number=1),

      type_info.ProtoString(
          name="name", field_number=2),

      type_info.ProtoUnsignedInteger(
          name="offset", field_number=3),

      type_info.ProtoString(
          name="vm", field_number=4),

      type_info.ProtoUnsignedInteger(
          name="value", field_number=5),

      type_info.ProtoString(
          name="svalue", field_number=6),

      type_info.ProtoString(
          name="reason", field_number=7),

      )


class FastVolatilityValues(rdfvalue.RDFProtoStruct):
  """A Faster implementation of VolatilityValues."""

  type_infos = type_info.TypeDescriptorSet(
      type_info.ProtoList(type_info.ProtoNested(
          name="values", field_number=1,
          nested=FastVolatilityValue))
      )


class RDFValueBenchmark(test_lib.MicroBenchmarks):
  """Microbenchmark tests for RDFProtos."""

  def testObjectCreation(self):
    """Compare the speed of object creation to raw protobufs."""
    test_proto = jobs_pb2.StatResponse(aff4path="aff4:/foo/bar")

    def RDFValueCreateAndSerialize():
      s = rdfvalue.StatEntry(aff4path="aff4:/foo/bar")
      s.SerializeToString()

    def RDFValueCreateAndSerializeFromProto():
      s = rdfvalue.StatEntry(test_proto)
      s.SerializeToString()

    def ProtoCreateAndSerialize():
      s = jobs_pb2.StatResponse(aff4path="aff4:/foo/bar")
      s.SerializeToString()

    def ProtoCreateAndSerializeSetValue():
      s = jobs_pb2.StatResponse()
      s.aff4path = "aff4:/foo/bar"
      s.SerializeToString()

      self.TimeIt(RDFValueCreateAndSerialize)

      self.TimeIt(RDFValueCreateAndSerializeFromProto)
      self.TimeIt(ProtoCreateAndSerialize, "Protobuf from keywords")

      self.TimeIt(ProtoCreateAndSerializeSetValue,
                  "Protobuf by value setting")

  def testObjectCreation2(self):

    def RDFValueCreateAndSerialize():
      s = rdfvalue.GRRMessage(name=u"foo", request_id=1, response_id=1,
                              session_id=u"session")
      s.SerializeToString()

    def ProtoCreateAndSerialize():
      s = jobs_pb2.GrrMessage(name=u"foo", request_id=1, response_id=1,
                              session_id=u"session")
      return len(s.SerializeToString())

    def RDFStructCreateAndSerialize():
      s = StructGrrMessage(name=u"foo", request_id=1, response_id=1,
                           session_id=u"session")

      return len(s.SerializeToString())

    self.TimeIt(RDFValueCreateAndSerialize,
                "RDFValue from keywords")

    self.TimeIt(ProtoCreateAndSerialize,
                "Protobuf from keywords")

    self.TimeIt(RDFStructCreateAndSerialize,
                "RDFStruct from keywords")

  def testRepeatedFields(self):
    """Test serialization and construction of repeated fields."""

    repeats = self.REPEATS / 100

    def RDFValueCreateAndSerialize():
      s = rdfvalue.VolatilityValues()
      for i in range(self.REPEATS):
        s.values.Append(type="test", name="foobar", value=i)

      return len(zlib.compress(s.SerializeToString()))

    def ProtoCreateAndSerialize():
      s = jobs_pb2.VolatilityValues()
      for i in range(self.REPEATS):
        s.values.add(type="test", name="foobar", value=i)

      return len(zlib.compress(s.SerializeToString()))

    def RDFStructCreateAndSerialize():
      s = FastVolatilityValues()

      for i in range(self.REPEATS):
        s.values.Append(type="test", name="foobar", value=i)

      return len(zlib.compress(s.SerializeToString()))

    self.TimeIt(RDFStructCreateAndSerialize, repetitions=repeats)

    self.TimeIt(RDFValueCreateAndSerialize, repetitions=repeats)

    self.TimeIt(ProtoCreateAndSerialize, repetitions=repeats)

  def testRepeatedFields2(self):
    """Test serialization and construction of repeated fields."""

    repeats = self.REPEATS / 100

    def RDFValueCreateAndSerialize():
      s = rdfvalue.MessageList()
      for i in range(self.REPEATS):
        s.job.Append(session_id="test", name="foobar", request_id=i,
                     payload=rdfvalue.GrrStatus())

      s.SerializeToString()

    def ProtoCreateAndSerialize():
      s = jobs_pb2.MessageList()
      for i in range(self.REPEATS):
        payload = jobs_pb2.GrrStatus()

        s.job.add(session_id="test", name="foobar", request_id=i,
                  args=payload.SerializeToString(), args_age=int(time.time()),
                  args_rdf_name=payload.__class__.__name__,
                  task_id=0)

      s.SerializeToString()

    self.TimeIt(RDFValueCreateAndSerialize, repetitions=repeats)

    self.TimeIt(ProtoCreateAndSerialize, repetitions=repeats)

  def testDecode(self):
    """Test decoding performance."""

    s = jobs_pb2.GrrMessage(name=u"foo", request_id=1, response_id=1,
                            session_id=u"session")
    data = s.SerializeToString()

    def ProtoDecode():
      new_s = jobs_pb2.GrrMessage()
      new_s.ParseFromString(data)

      self.assertEqual(new_s.session_id, "session")

    def RDFStructDecode():
      new_s = StructGrrMessage()
      new_s.ParseFromString(data)

      self.assertEqual(new_s.session_id, "session")

      self.TimeIt(RDFStructDecode)

      self.TimeIt(ProtoDecode)

  def testEncodeDecode(self):
    """Test performance of encode/decode cycle."""

    def Check(s, new_s):
      self.assertEqual(s.name, new_s.name)
      self.assertEqual(s.name, u"foo")
      self.assertEqual(s.request_id, new_s.request_id)
      self.assertEqual(s.request_id, 1)
      self.assertEqual(s.response_id, new_s.response_id)
      self.assertEqual(s.response_id, 1)
      self.assertEqual(s.session_id, new_s.session_id)
      self.assertEqual(s.session_id, u"session")

    def ProtoEncodeDecode():
      s = jobs_pb2.GrrMessage(name=u"foo", request_id=1, response_id=1,
                              session_id=u"session")
      data = s.SerializeToString()

      new_s = jobs_pb2.GrrMessage()
      new_s.ParseFromString(data)

      return s, new_s

    def RDFStructEncodeDecode():
      s = StructGrrMessage(name=u"foo", request_id=1, response_id=1,
                           session_id=u"session")
      data = s.SerializeToString()

      new_s = StructGrrMessage(initializer=data)

      return s, new_s

    # Make sure everything is sane first.
    Check(*ProtoEncodeDecode())
    Check(*RDFStructEncodeDecode())

    self.TimeIt(RDFStructEncodeDecode)
    self.TimeIt(ProtoEncodeDecode)
