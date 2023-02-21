#!/usr/bin/env python
"""Test Protobuf behavior."""


from absl.testing import absltest

from grr_response_proto import tests_pb2


class BooleanToEnumMigrationTest(absltest.TestCase):

  def testBooleansAreParsedAsEnums(self):
    a = tests_pb2.BoolMessage()
    b = tests_pb2.EnumMessage()
    b.ParseFromString(a.SerializeToString())
    self.assertEqual(b.foo, tests_pb2.EnumMessage.NestedEnum.NULL)

    a = tests_pb2.BoolMessage(foo=False)
    b = tests_pb2.EnumMessage()
    b.ParseFromString(a.SerializeToString())
    self.assertEqual(b.foo, tests_pb2.EnumMessage.NestedEnum.NULL)

    a = tests_pb2.BoolMessage(foo=True)
    b = tests_pb2.EnumMessage()
    b.ParseFromString(a.SerializeToString())
    self.assertEqual(b.foo, tests_pb2.EnumMessage.NestedEnum.ONE)

  def testEnumsAreParsedAsBooleans(self):
    a = tests_pb2.EnumMessage()
    b = tests_pb2.BoolMessage()
    b.ParseFromString(a.SerializeToString())
    self.assertIs(b.foo, False)

    a = tests_pb2.EnumMessage(foo="NULL")
    b = tests_pb2.BoolMessage()
    b.ParseFromString(a.SerializeToString())
    self.assertIs(b.foo, False)

    a = tests_pb2.EnumMessage(foo="ONE")
    b = tests_pb2.BoolMessage()
    b.ParseFromString(a.SerializeToString())
    self.assertIs(b.foo, True)

  def testNewEnumOptionIsBackwardsCompatibleToTrue(self):
    a = tests_pb2.EnumMessage(foo="TWO")
    b = tests_pb2.BoolMessage()
    b.ParseFromString(a.SerializeToString())
    self.assertIs(b.foo, True)


if __name__ == "__main__":
  absltest.main()
