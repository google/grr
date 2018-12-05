#!/usr/bin/env python
"""This module tests the RDFValue implementation for performance."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from builtins import range  # pylint: disable=redefined-builtin
from future.utils import iteritems

from grr_response_core.lib import flags
from grr_response_core.lib import type_info
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import jobs_pb2
from grr_response_proto import knowledge_base_pb2
from grr.test_lib import benchmark_test_lib
from grr.test_lib import test_lib


class StructGrrMessage(rdf_structs.RDFProtoStruct):
  """A serialization agnostic GrrMessage."""

  type_description = type_info.TypeDescriptorSet(
      rdf_structs.ProtoString(
          name="session_id",
          field_number=1,
          description="Every Flow has a unique session id."),
      rdf_structs.ProtoUnsignedInteger(
          name="request_id",
          field_number=2,
          description="This message is in response to this request number"),
      rdf_structs.ProtoUnsignedInteger(
          name="response_id",
          field_number=3,
          description="Responses for each request."),
      rdf_structs.ProtoString(
          name="name",
          field_number=4,
          description=("This is the name of the client action that will be "
                       "executed. It is set by the flow and is executed by "
                       "the client.")),
      rdf_structs.ProtoBinary(
          name="args",
          field_number=5,
          description="This field contains an encoded rdfvalue."),
      rdf_structs.ProtoString(
          name="source",
          field_number=6,
          description=("Client name where the message came from (This is "
                       "copied from the MessageList)")),
  )


class FastGrrMessageList(rdf_structs.RDFProtoStruct):
  """A Faster implementation of GrrMessageList."""

  type_description = type_info.TypeDescriptorSet(
      rdf_structs.ProtoList(
          rdf_structs.ProtoEmbedded(
              name="job", field_number=1, nested=StructGrrMessage)))


class RDFValueBenchmark(benchmark_test_lib.AverageMicroBenchmarks):
  """Microbenchmark tests for RDFProtos."""

  REPEATS = 1000
  units = "us"

  USER_ACCOUNT = dict(
      username=u"user",
      full_name=u"John Smith",
      last_logon=10000,
      userdomain=u"Some domain name",
      homedir=u"/home/user",
      sid=u"some sid")

  def testObjectCreation(self):
    """Compare the speed of object creation to raw protobufs."""
    test_proto = knowledge_base_pb2.User(**self.USER_ACCOUNT)
    test_proto = test_proto.SerializeToString()

    def RDFStructCreateAndSerialize():
      s = rdf_client.User(**self.USER_ACCOUNT)
      s.SerializeToString()

    def RDFStructCreateAndSerializeSetValue():
      s = rdf_client.User()
      for k, v in iteritems(self.USER_ACCOUNT):
        setattr(s, k, v)

      s.SerializeToString()

    def RDFStructCreateAndSerializeFromProto():
      s = rdf_client.User.FromSerializedString(test_proto)
      s.SerializeToString()

    def ProtoCreateAndSerialize():
      s = knowledge_base_pb2.User(**self.USER_ACCOUNT)
      s.SerializeToString()

    def ProtoCreateAndSerializeSetValue():
      s = knowledge_base_pb2.User()
      for k, v in iteritems(self.USER_ACCOUNT):
        setattr(s, k, v)

      s.SerializeToString()

    def ProtoCreateAndSerializeFromProto():
      s = knowledge_base_pb2.User()
      s.ParseFromString(test_proto)
      self.assertEqual(s.SerializeToString(), test_proto)

    self.TimeIt(RDFStructCreateAndSerialize,
                "SProto Create from keywords and serialize.")

    self.TimeIt(RDFStructCreateAndSerializeSetValue,
                "SProto Create, Set And Serialize")

    self.TimeIt(RDFStructCreateAndSerializeFromProto,
                "SProto from serialized and serialize.")

    self.TimeIt(ProtoCreateAndSerialize,
                "Protobuf from keywords and serialize.")

    self.TimeIt(ProtoCreateAndSerializeSetValue,
                "Protobuf Create, Set and serialize")

    self.TimeIt(ProtoCreateAndSerializeFromProto,
                "Protobuf from serialized and serialize.")

  def testObjectCreation2(self):

    def ProtoCreateAndSerialize():
      s = jobs_pb2.GrrMessage(
          name=u"foo", request_id=1, response_id=1, session_id=u"session")
      return len(s.SerializeToString())

    def RDFStructCreateAndSerialize():
      s = StructGrrMessage(
          name=u"foo", request_id=1, response_id=1, session_id=u"session")

      return len(s.SerializeToString())

    self.TimeIt(ProtoCreateAndSerialize, "Protobuf from keywords")

    self.TimeIt(RDFStructCreateAndSerialize, "RDFStruct from keywords")

  def testDecodeRepeatedFields(self):
    """Test decoding of repeated fields."""

    repeats = self.REPEATS // 50
    s = jobs_pb2.MessageList()
    for i in range(self.REPEATS):
      s.job.add(session_id="test", name="foobar", request_id=i)

    test_data = s.SerializeToString()

    def ProtoDecode():
      s = jobs_pb2.MessageList()
      s.ParseFromString(test_data)

      self.assertEqual(s.job[100].request_id, 100)

    def SProtoDecode():
      s = FastGrrMessageList.FromSerializedString(test_data)
      self.assertEqual(s.job[100].request_id, 100)

    self.TimeIt(SProtoDecode, "SProto Repeated Decode", repetitions=repeats)

    self.TimeIt(ProtoDecode, "Protobuf Repeated Decode", repetitions=repeats)

  def testRepeatedFields(self):
    """Test serialization and construction of repeated fields."""

    repeats = self.REPEATS // 50

    def ProtoCreateAndSerialize():
      s = jobs_pb2.MessageList()
      for i in range(self.REPEATS):
        s.job.add(session_id="test", name="foobar", request_id=i)

      return len(s.SerializeToString())

    def RDFStructCreateAndSerialize():
      s = FastGrrMessageList()

      for i in range(self.REPEATS):
        s.job.Append(session_id="test", name="foobar", request_id=i)

      return len(s.SerializeToString())

    self.TimeIt(
        RDFStructCreateAndSerialize,
        "RDFStruct Repeated Fields",
        repetitions=repeats)

    self.TimeIt(
        ProtoCreateAndSerialize,
        "Protobuf Repeated Fields",
        repetitions=repeats)

    # Check that we can unserialize a protobuf encoded using the standard
    # library.
    s = jobs_pb2.MessageList()
    for i in range(self.REPEATS):
      s.job.add(session_id="test", name="foobar", request_id=i)

    serialized = s.SerializeToString()
    unserialized = FastGrrMessageList.FromSerializedString(serialized)
    self.assertLen(unserialized.job, len(s.job))

    self.assertEqual(unserialized.job[134].session_id, "test")
    self.assertEqual(unserialized.job[100].request_id, 100)

  def testDecode(self):
    """Test decoding performance."""

    s = jobs_pb2.GrrMessage(
        name=u"foo", request_id=1, response_id=1, session_id=u"session")
    data = s.SerializeToString()

    def ProtoDecode():
      new_s = jobs_pb2.GrrMessage()
      new_s.ParseFromString(data)

      self.assertEqual(new_s.session_id, "session")
      self.assertEqual(new_s.session_id.__class__, unicode)

    def RDFStructDecode():
      new_s = StructGrrMessage()
      new_s.ParseFromString(data)

      self.assertEqual(new_s.session_id, "session")
      self.assertEqual(new_s.session_id.__class__, unicode)

    self.TimeIt(RDFStructDecode)
    self.TimeIt(ProtoDecode)

  def testDecode2(self):
    """Test decoding performance.

    This benchmarks the lazy decoding feature where a large protobuf is decoded
    but only a few fields are examined.
    """

    s = knowledge_base_pb2.User(**self.USER_ACCOUNT)

    data = s.SerializeToString()

    def ProtoDecode():
      new_s = knowledge_base_pb2.User()
      new_s.ParseFromString(data)

      self.assertEqual(new_s.username, "user")
      self.assertEqual(new_s.username.__class__, unicode)

    def RDFStructDecode():
      new_s = rdf_client.User()
      new_s.ParseFromString(data)

      self.assertEqual(new_s.username, "user")
      self.assertEqual(new_s.username.__class__, unicode)

    self.TimeIt(RDFStructDecode)
    self.TimeIt(ProtoDecode)

  def testEncode(self):
    """Comparing encoding speed of a typical protobuf."""
    s = jobs_pb2.GrrMessage(
        name=u"foo", request_id=1, response_id=1, session_id=u"session")
    serialized = s.SerializeToString()

    def ProtoEncode():
      s1 = jobs_pb2.GrrMessage(
          name=u"foo", request_id=1, response_id=1, session_id=u"session")

      test = s1.SerializeToString()
      self.assertLen(serialized, len(test))

    def RDFStructEncode():
      s2 = StructGrrMessage(
          name=u"foo", request_id=1, response_id=1, session_id=u"session")

      test = s2.SerializeToString()
      self.assertLen(serialized, len(test))

    self.TimeIt(RDFStructEncode)
    self.TimeIt(ProtoEncode)

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
      s = jobs_pb2.GrrMessage(
          name=u"foo", request_id=1, response_id=1, session_id=u"session")
      data = s.SerializeToString()

      new_s = jobs_pb2.GrrMessage()
      new_s.ParseFromString(data)

      return s, new_s

    def RDFStructEncodeDecode():
      s = StructGrrMessage(
          name=u"foo", request_id=1, response_id=1, session_id=u"session")
      data = s.SerializeToString()

      new_s = StructGrrMessage.FromSerializedString(data)

      return s, new_s

    # Make sure everything is sane first.
    Check(*ProtoEncodeDecode())
    Check(*RDFStructEncodeDecode())

    self.TimeIt(RDFStructEncodeDecode)
    self.TimeIt(ProtoEncodeDecode)

  def testDecodeEncode(self):
    """Test performance of decode/encode cycle."""

    s = jobs_pb2.GrrMessage(
        name=u"foo", request_id=1, response_id=1, session_id=u"session")
    data = s.SerializeToString()

    def ProtoDecodeEncode():
      new_s = jobs_pb2.GrrMessage()
      new_s.ParseFromString(data)
      new_s.SerializeToString()

    def RDFStructDecodeEncode():
      new_s = StructGrrMessage.FromSerializedString(data)
      new_s.SerializeToString()

    self.TimeIt(RDFStructDecodeEncode)
    self.TimeIt(ProtoDecodeEncode)


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
