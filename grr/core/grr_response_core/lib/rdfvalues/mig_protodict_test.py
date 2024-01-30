#!/usr/bin/env python
from absl.testing import absltest

from grr_response_core.lib.rdfvalues import mig_protodict
from grr_response_proto import jobs_pb2


class FromProtoDictToNativeDictTest(absltest.TestCase):

  def testFromProtoDictToNativeDict(self):
    expected = {"a": 1, "b": 2, "c": "d"}
    proto = jobs_pb2.Dict(
        dat=[
            jobs_pb2.KeyValue(
                k=jobs_pb2.DataBlob(string="a"), v=jobs_pb2.DataBlob(integer=1)
            ),
            jobs_pb2.KeyValue(
                k=jobs_pb2.DataBlob(string="b"), v=jobs_pb2.DataBlob(integer=2)
            ),
            jobs_pb2.KeyValue(
                k=jobs_pb2.DataBlob(string="c"), v=jobs_pb2.DataBlob(string="d")
            ),
        ]
    )
    got = mig_protodict.FromProtoDictToNativeDict(proto)
    self.assertEqual(expected, got)


class FromNativeDictToProtoDictTest(absltest.TestCase):

  def testFromNativeDictToProtoDict(self):
    native = {"a": 1, "b": 2, "c": "d"}
    expected = jobs_pb2.Dict(
        dat=[
            jobs_pb2.KeyValue(
                k=jobs_pb2.DataBlob(string="a"), v=jobs_pb2.DataBlob(integer=1)
            ),
            jobs_pb2.KeyValue(
                k=jobs_pb2.DataBlob(string="b"), v=jobs_pb2.DataBlob(integer=2)
            ),
            jobs_pb2.KeyValue(
                k=jobs_pb2.DataBlob(string="c"), v=jobs_pb2.DataBlob(string="d")
            ),
        ]
    )
    got = mig_protodict.FromNativeDictToProtoDict(native)
    self.assertEqual(expected, got)


class FromProtoAttributedDictToNativeDictTest(absltest.TestCase):

  def testFromProtoAttributedDictToNativeDict(self):
    expected = {"a": 1, "b": 2, "c": "d"}
    proto = jobs_pb2.AttributedDict(
        dat=[
            jobs_pb2.KeyValue(
                k=jobs_pb2.DataBlob(string="a"), v=jobs_pb2.DataBlob(integer=1)
            ),
            jobs_pb2.KeyValue(
                k=jobs_pb2.DataBlob(string="b"), v=jobs_pb2.DataBlob(integer=2)
            ),
            jobs_pb2.KeyValue(
                k=jobs_pb2.DataBlob(string="c"), v=jobs_pb2.DataBlob(string="d")
            ),
        ]
    )
    got = mig_protodict.FromProtoAttributedDictToNativeDict(proto)
    self.assertEqual(expected, got)


class FromNativeDictToProtoAttributedDictTest(absltest.TestCase):

  def testFromNativeDictToProtoAttributedDict(self):
    native = {"a": 1, "b": 2, "c": "d"}
    expected = jobs_pb2.AttributedDict(
        dat=[
            jobs_pb2.KeyValue(
                k=jobs_pb2.DataBlob(string="a"), v=jobs_pb2.DataBlob(integer=1)
            ),
            jobs_pb2.KeyValue(
                k=jobs_pb2.DataBlob(string="b"), v=jobs_pb2.DataBlob(integer=2)
            ),
            jobs_pb2.KeyValue(
                k=jobs_pb2.DataBlob(string="c"), v=jobs_pb2.DataBlob(string="d")
            ),
        ]
    )
    got = mig_protodict.FromNativeDictToProtoAttributedDict(native)
    self.assertEqual(expected, got)


if __name__ == "__main__":
  absltest.main()
