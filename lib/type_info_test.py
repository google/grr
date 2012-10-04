#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
# Copyright 2012 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.





from grr.client import conf

from grr.artifacts import win_artifacts
from grr.lib import test_lib
from grr.lib import type_info
from grr.proto import jobs_pb2


class TypeInfoTest(test_lib.GRRBaseTest):

  def testTypeInfoBoolObjects(self):
    """Test the type info objects behave as expected."""
    a = type_info.Bool()
    self.assertRaises(type_info.TypeValueError, a.Validate, 1)
    self.assertRaises(type_info.TypeValueError, a.Validate, None)
    a.Validate(True)
    self.assertEqual(a.DecodeString("tRue"), True)
    self.assertRaises(type_info.DecodeError, a.DecodeString, "None")

    a = type_info.BoolOrNone()
    self.assertRaises(type_info.TypeValueError, a.Validate, 1)
    a.Validate(None)
    a.Validate(False)
    a.DecodeString(u"none")
    a.DecodeString("false")

  def testTypeInfoStringObjects(self):
    """Test the type info objects behave as expected."""
    a = type_info.String()
    self.assertRaises(type_info.TypeValueError, a.Validate, 1)
    self.assertRaises(type_info.TypeValueError, a.Validate, None)
    a.Validate("test")
    a.Validate(u"test")
    a.Validate(u"/test-Îñ铁网åţî[öñåļ(îžåţîờñ")
    self.assertEqual(a.DecodeString(u"/test-Îñ铁网åţî[öñåļ(îžåţîờñ"),
                     u"/test-Îñ铁网åţî[öñåļ(îžåţîờñ")
    self.assertEqual(a.DecodeString("None"), "None")

    a = type_info.StringOrNone()
    self.assertRaises(type_info.TypeValueError, a.Validate, 1)
    a.Validate(None)
    a.Validate("test")
    self.assertTrue(a.DecodeString(u"none") is None)

  def testTypeInfoEnumObjects(self):
    """Test the type info objects behave as expected."""
    a = type_info.ProtoEnum(jobs_pb2.Path, "PathType")
    self.assertRaises(type_info.TypeValueError, a.Validate, 9999)
    self.assertRaises(type_info.TypeValueError, a.Validate, None)
    a.Validate(jobs_pb2.Path.OS)
    self.assertEqual(a.DecodeString("-1"), -1)
    self.assertEqual(a.DecodeString("2"), 2)
    self.assertRaises(type_info.DecodeError, a.DecodeString, "test")

    a = type_info.ProtoEnumOrNone(jobs_pb2.Path, "PathType")
    self.assertRaises(type_info.TypeValueError, a.Validate, 9999)
    a.Validate(None)
    a.Validate(jobs_pb2.Path.TSK)
    self.assertTrue(a.DecodeString(u"none") is None)
    a.DecodeString("1")

  def testTypeInfoProtoObjects(self):
    """Test the type info objects behave as expected."""
    a = type_info.Proto(jobs_pb2.Path)
    self.assertRaises(type_info.TypeValueError, a.Validate, "test")
    self.assertRaises(type_info.TypeValueError, a.Validate, None)
    a.Validate(jobs_pb2.Path())

    # No decode functionality yet.
    self.assertRaises(type_info.DecodeError, a.DecodeString, "test")

    a = type_info.ProtoOrNone(jobs_pb2.Path)
    self.assertRaises(type_info.TypeValueError, a.Validate, "test")
    a.Validate(None)
    a.Validate(jobs_pb2.Path())
    self.assertTrue(a.DecodeString(u"none") is None)

  def testTypeInfoListProtoObjects(self):
    """Test the type info list proto objects behave as expected."""
    a = type_info.ListProto(jobs_pb2.Path)
    self.assertRaises(type_info.TypeValueError, a.Validate, "test")
    self.assertRaises(type_info.TypeValueError, a.Validate, 1)
    self.assertRaises(type_info.TypeValueError, a.Validate, [1, 2])
    self.assertRaises(type_info.TypeValueError, a.Validate, None)
    a.Validate([jobs_pb2.Path()])

    # Reject mixed protos.
    self.assertRaises(type_info.TypeValueError, a.Validate,
                      [jobs_pb2.Path(), jobs_pb2.GrrMessage()])

    # No decode functionality yet.
    self.assertRaises(type_info.DecodeError, a.DecodeString, "test")

    a = type_info.ListProtoOrNone(jobs_pb2.Path)
    a.Validate(None)

  def testTypeInfoNumberObjects(self):
    """Test the type info objects behave as expected."""
    a = type_info.Number()
    self.assertRaises(type_info.TypeValueError, a.Validate, "1")
    self.assertRaises(type_info.TypeValueError, a.Validate, None)
    a.Validate(1231232)
    a.Validate(-2)
    self.assertEqual(a.DecodeString("1234"), 1234)
    self.assertEqual(a.DecodeString("-1234"), -1234)
    self.assertRaises(type_info.DecodeError, a.DecodeString, "None")

    a = type_info.NumberOrNone()
    self.assertRaises(type_info.TypeValueError, a.Validate, "a1")
    a.Validate(None)
    a.Validate(1234)
    a.DecodeString(u"none")
    a.DecodeString("123")
    a.DecodeString("0")

  def testTypeInfoListObjects(self):
    """Test List objects."""
    a = type_info.List(type_info.Number())
    self.assertRaises(type_info.TypeValueError, a.Validate, 1)
    self.assertRaises(type_info.TypeValueError, a.Validate, "test")
    self.assertRaises(type_info.TypeValueError, a.Validate, None)
    self.assertRaises(type_info.TypeValueError, a.Validate, ["test"])
    self.assertRaises(type_info.TypeValueError, a.Validate, [jobs_pb2.Path()])
    a.Validate([1, 2, 3])
    self.assertRaises(type_info.DecodeError, a.DecodeString, "None")

    a = type_info.ListOrNone(type_info.Number())
    self.assertTrue(a.DecodeString(u"none") is None)

  def testTypeInfoArtifactObjects(self):
    """Test list List objects."""
    a = type_info.ArtifactList()
    self.assertRaises(type_info.TypeValueError, a.Validate, 1)
    self.assertRaises(type_info.TypeValueError, a.Validate, None)
    a.Validate(["ApplicationEventLog"])
    self.assertRaises(type_info.TypeValueError, a.Validate, ["Invalid"])
    self.assertRaises(type_info.TypeValueError, a.Validate,
                      [win_artifacts.ApplicationEventLog])

    a = type_info.ArtifactListOrNone()
    self.assertTrue(a.DecodeString(u"none") is None)


def main(args):
  test_lib.main(args)

if __name__ == "__main__":
  conf.StartMain(main)
