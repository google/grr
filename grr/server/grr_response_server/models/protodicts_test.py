#!/usr/bin/env python
from absl.testing import absltest

from grr_response_server.models import protodicts


class DataBlobTest(absltest.TestCase):

  def testBool(self):
    self.assertEqual(protodicts.DataBlob(True).boolean, True)

  def testInt(self):
    self.assertEqual(protodicts.DataBlob(1337).integer, 1337)

  def testFloat(self):
    self.assertEqual(protodicts.DataBlob(0.5).float, 0.5)

  def testBytes(self):
    self.assertEqual(protodicts.DataBlob(b"\x00\xff\x00").data, b"\x00\xff\x00")

  def testStr(self):
    self.assertEqual(protodicts.DataBlob("foobar").string, "foobar")

  def testList(self):
    proto = protodicts.DataBlob([1, 3, 3, 7])

    self.assertLen(proto.list.content, 4)
    self.assertEqual(proto.list.content[0].integer, 1)
    self.assertEqual(proto.list.content[1].integer, 3)
    self.assertEqual(proto.list.content[2].integer, 3)
    self.assertEqual(proto.list.content[3].integer, 7)

  def testDict(self):
    proto = protodicts.DataBlob({
        "foo": 42,
        "bar": 1337,
    })

    self.assertLen(proto.dict.dat, 2)
    self.assertEqual(proto.dict.dat[0].k.string, "foo")
    self.assertEqual(proto.dict.dat[0].v.integer, 42)
    self.assertEqual(proto.dict.dat[1].k.string, "bar")
    self.assertEqual(proto.dict.dat[1].v.integer, 1337)


class BlobArrayTest(absltest.TestCase):

  def testEmpty(self):
    proto = protodicts.BlobArray([])

    self.assertEmpty(proto.content)

  def testSingleton(self):
    proto = protodicts.BlobArray(["foo"])

    self.assertLen(proto.content, 1)
    self.assertEqual(proto.content[0].string, "foo")

  def testHomogeneous(self):
    proto = protodicts.BlobArray(["foo", "bar", "baz"])

    self.assertLen(proto.content, 3)
    self.assertEqual(proto.content[0].string, "foo")
    self.assertEqual(proto.content[1].string, "bar")
    self.assertEqual(proto.content[2].string, "baz")

  def testHeterogeneous(self):
    proto = protodicts.BlobArray([42, "foo", 0.5])

    self.assertLen(proto.content, 3)
    self.assertEqual(proto.content[0].integer, 42)
    self.assertEqual(proto.content[1].string, "foo")
    self.assertEqual(proto.content[2].float, 0.5)

  def testRepeated(self):
    proto = protodicts.BlobArray([1, 3, 3, 7])

    self.assertLen(proto.content, 4)
    self.assertEqual(proto.content[0].integer, 1)
    self.assertEqual(proto.content[1].integer, 3)
    self.assertEqual(proto.content[2].integer, 3)
    self.assertEqual(proto.content[3].integer, 7)

  def testNested(self):
    proto = protodicts.BlobArray([["foo", "bar"], ["quux"]])

    self.assertLen(proto.content, 2)
    self.assertLen(proto.content[0].list.content, 2)
    self.assertLen(proto.content[1].list.content, 1)
    self.assertEqual(proto.content[0].list.content[0].string, "foo")
    self.assertEqual(proto.content[0].list.content[1].string, "bar")
    self.assertEqual(proto.content[1].list.content[0].string, "quux")


class DictTest(absltest.TestCase):

  def testEmpty(self):
    proto = protodicts.Dict({})

    self.assertEmpty(proto.dat)

  def testSingleton(self):
    proto = protodicts.Dict({"foo": 42})

    self.assertLen(proto.dat, 1)
    self.assertEqual(proto.dat[0].k.string, "foo")
    self.assertEqual(proto.dat[0].v.integer, 42)

  def testHomogeneous(self):
    proto = protodicts.Dict({
        "foo": 0xC0DE,
        "bar": 0xBEEF,
        "quux": 0xC0FE,
    })

    self.assertLen(proto.dat, 3)
    self.assertEqual(proto.dat[0].k.string, "foo")
    self.assertEqual(proto.dat[0].v.integer, 0xC0DE)
    self.assertEqual(proto.dat[1].k.string, "bar")
    self.assertEqual(proto.dat[1].v.integer, 0xBEEF)
    self.assertEqual(proto.dat[2].k.string, "quux")
    self.assertEqual(proto.dat[2].v.integer, 0xC0FE)

  def testHeterogeneous(self):
    proto = protodicts.Dict({
        "foo": 0.5,
        1337: b"\x00\xFF\x00",
    })

    self.assertLen(proto.dat, 2)
    self.assertEqual(proto.dat[0].k.string, "foo")
    self.assertEqual(proto.dat[0].v.float, 0.5)
    self.assertEqual(proto.dat[1].k.integer, 1337)
    self.assertEqual(proto.dat[1].v.data, b"\x00\xFF\x00")

  def testNested(self):
    proto = protodicts.Dict({
        "foo": {
            "bar": "baz",
        },
        "quux": {
            "norf": "thud",
        },
    })

    self.assertLen(proto.dat, 2)
    self.assertLen(proto.dat[0].v.dict.dat, 1)
    self.assertLen(proto.dat[1].v.dict.dat, 1)
    self.assertEqual(proto.dat[0].k.string, "foo")
    self.assertEqual(proto.dat[0].v.dict.dat[0].k.string, "bar")
    self.assertEqual(proto.dat[0].v.dict.dat[0].v.string, "baz")
    self.assertEqual(proto.dat[1].k.string, "quux")
    self.assertEqual(proto.dat[1].v.dict.dat[0].k.string, "norf")
    self.assertEqual(proto.dat[1].v.dict.dat[0].v.string, "thud")


if __name__ == "__main__":
  absltest.main()
