#!/usr/bin/env python
from absl.testing import absltest
from absl.testing import parameterized as absltest_parametrized

from grr_response_server import rrg_wmi
from grr.test_lib import rrg_wmi_test_lib
from grr_response_proto.rrg.action import query_wmi_pb2 as rrg_query_wmi_pb2


class SInt8Test(absltest_parametrized.TestCase):

  @absltest_parametrized.parameters([
      0,
      42,
      -42,
      2**7 - 1,
      -(2**7),
  ])
  def testValue(self, value: int) -> None:
    self.assertEqual(
        rrg_wmi.SInt8(rrg_wmi_test_lib.SInt8(value).value),
        value,
    )

  def testNone(self) -> None:
    self.assertIsNone(rrg_wmi.SInt8(rrg_wmi_test_lib.Null()))

  @absltest_parametrized.parameters([-(2**7) - 1, 2**7])
  def testOutOfRange(self, value: int) -> None:
    with self.assertRaisesRegex(ValueError, "Out-of-range sint8 value"):
      rrg_wmi.SInt8(rrg_query_wmi_pb2.Value(int=value))


class SInt16Test(absltest_parametrized.TestCase):

  @absltest_parametrized.parameters([
      0,
      42,
      -42,
      2**7 - 1,
      -(2**7),
      2**15 - 1,
      -(2**15),
  ])
  def testValue(self, value: int) -> None:
    self.assertEqual(
        rrg_wmi.SInt16(rrg_wmi_test_lib.SInt16(value).value),
        value,
    )

  def testNone(self) -> None:
    self.assertIsNone(rrg_wmi.SInt16(rrg_wmi_test_lib.Null()))

  @absltest_parametrized.parameters([-(2**15) - 1, 2**15])
  def testOutOfRange(self, value: int) -> None:
    with self.assertRaisesRegex(ValueError, "Out-of-range sint16 value"):
      rrg_wmi.SInt16(rrg_query_wmi_pb2.Value(int=value))


class SInt32Test(absltest_parametrized.TestCase):

  @absltest_parametrized.parameters([
      0,
      42,
      -42,
      2**7 - 1,
      -(2**7),
      2**15 - 1,
      -(2**15),
      2**31 - 1,
      -(2**31),
  ])
  def testValue(self, value: int) -> None:
    self.assertEqual(
        rrg_wmi.SInt32(rrg_wmi_test_lib.SInt32(value).value),
        value,
    )

  def testNone(self) -> None:
    self.assertIsNone(rrg_wmi.SInt32(rrg_wmi_test_lib.Null()))

  @absltest_parametrized.parameters([-(2**31) - 1, 2**31])
  def testOutOfRange(self, value: int) -> None:
    with self.assertRaisesRegex(ValueError, "Out-of-range sint32 value"):
      rrg_wmi.SInt32(rrg_query_wmi_pb2.Value(int=value))


class SInt64Test(absltest_parametrized.TestCase):

  @absltest_parametrized.parameters([
      0,
      42,
      -42,
      2**7 - 1,
      -(2**7),
      2**15 - 1,
      -(2**15),
      2**31 - 1,
      -(2**31),
      2**63 - 1,
      -(2**63),
  ])
  def testValue(self, value: int) -> None:
    self.assertEqual(
        rrg_wmi.SInt64(rrg_wmi_test_lib.SInt64(value).value),
        value,
    )

  def testNone(self) -> None:
    self.assertIsNone(rrg_wmi.SInt64(rrg_wmi_test_lib.Null()))

  @absltest_parametrized.parameters([str(-(2**63) - 1), str(2**63)])
  def testOutOfRange(self, value: str) -> None:
    with self.assertRaisesRegex(ValueError, "Out-of-range sint64 value"):
      rrg_wmi.SInt64(rrg_query_wmi_pb2.Value(string=value))


class Real32Test(absltest_parametrized.TestCase):

  @absltest_parametrized.parameters([
      0.0,
      1.0,
      -1.0,
      3.14,
  ])
  def testValue(self, value: float) -> None:
    value_float = rrg_wmi.Real32(rrg_wmi_test_lib.Real32(value).value)

    assert value_float is not None
    self.assertAlmostEqual(value_float, value, places=5)

  def testNone(self) -> None:
    self.assertIsNone(rrg_wmi.Real32(rrg_wmi_test_lib.Null()))


class Real64Test(absltest_parametrized.TestCase):

  @absltest_parametrized.parameters([
      0.0,
      1.0,
      -1.0,
      3.14,
  ])
  def testValue(self, value: float) -> None:
    value_float = rrg_wmi.Real64(rrg_wmi_test_lib.Real64(value).value)

    assert value_float is not None
    self.assertAlmostEqual(value_float, value, places=5)

  def testNone(self) -> None:
    self.assertIsNone(rrg_wmi.Real64(rrg_wmi_test_lib.Null()))


class UInt8Test(absltest_parametrized.TestCase):

  @absltest_parametrized.parameters([
      0,
      42,
      2**8 - 1,
  ])
  def testValue(self, value: int) -> None:
    self.assertEqual(
        rrg_wmi.UInt8(rrg_wmi_test_lib.UInt8(value).value),
        value,
    )

  def testNone(self) -> None:
    self.assertIsNone(rrg_wmi.UInt8(rrg_wmi_test_lib.Null()))

  @absltest_parametrized.parameters([2**8, 2**16])
  def testOutOfRange(self, value: int) -> None:
    with self.assertRaisesRegex(ValueError, "Out-of-range uint8 value"):
      rrg_wmi.UInt8(rrg_query_wmi_pb2.Value(uint=value))


class UInt16Test(absltest_parametrized.TestCase):

  @absltest_parametrized.parameters([
      0,
      42,
      2**8 - 1,
      2**16 - 1,
  ])
  def testValue(self, value: int) -> None:
    self.assertEqual(
        rrg_wmi.UInt16(rrg_wmi_test_lib.UInt16(value).value),
        value,
    )

  def testNone(self) -> None:
    self.assertIsNone(rrg_wmi.UInt16(rrg_wmi_test_lib.Null()))

  @absltest_parametrized.parameters([-1, 2**16])
  def testOutOfRange(self, value: int) -> None:
    with self.assertRaisesRegex(ValueError, "Out-of-range uint16 value"):
      rrg_wmi.UInt16(rrg_query_wmi_pb2.Value(int=value))


class UInt32Test(absltest_parametrized.TestCase):

  @absltest_parametrized.parameters([
      0,
      42,
      2**8 - 1,
      2**16 - 1,
      2**32 - 1,
  ])
  def testValue(self, value: int) -> None:
    self.assertEqual(
        rrg_wmi.UInt32(rrg_wmi_test_lib.UInt32(value).value),
        value,
    )

  def testNone(self) -> None:
    self.assertIsNone(rrg_wmi.UInt32(rrg_wmi_test_lib.Null()))

  @absltest_parametrized.parameters([-(2**31) - 1, 2**31])
  def testOutOfRange(self, value: int) -> None:
    with self.assertRaisesRegex(ValueError, "Out-of-range uint32 value"):
      rrg_wmi.UInt32(rrg_query_wmi_pb2.Value(int=value))


class UInt64Test(absltest_parametrized.TestCase):

  @absltest_parametrized.parameters([
      0,
      42,
      2**8 - 1,
      2**16 - 1,
      2**32 - 1,
      2**64 - 1,
  ])
  def testValue(self, value: int) -> None:
    self.assertEqual(
        rrg_wmi.UInt64(rrg_wmi_test_lib.UInt64(value).value),
        value,
    )

  def testNone(self) -> None:
    self.assertIsNone(rrg_wmi.UInt64(rrg_wmi_test_lib.Null()))

  @absltest_parametrized.parameters(["-1", str(2**64)])
  def testOutOfRange(self, value: str) -> None:
    with self.assertRaisesRegex(ValueError, "Out-of-range uint64 value"):
      rrg_wmi.UInt64(rrg_query_wmi_pb2.Value(string=value))


if __name__ == "__main__":
  absltest.main()
