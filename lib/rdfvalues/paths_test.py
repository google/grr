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

"""These are tests for the RDFPathSpec implementation."""




from grr.lib import rdfvalue
from grr.lib.rdfvalues import test_base
from grr.proto import jobs_pb2


class RDFPathSpecTest(test_base.RDFProtoTestCase):
  """Test the RDFPathSpec implementation."""

  rdfvalue_class = rdfvalue.RDFPathSpec

  def CheckRDFValue(self, rdfproto, sample):
    """Check that the rdfproto is the same as the sample."""
    super(RDFPathSpecTest, self).CheckRDFValue(rdfproto, sample)

    self.assertEqual(rdfproto.path, sample.path)
    self.assertEqual(rdfproto.pathtype, sample.pathtype)

  def GenerateSample(self, number=0):
    """Make a sample RDFPathSpec instance."""
    return rdfvalue.RDFPathSpec(path="/%s/" % number, pathtype=number)

  def testPop(self):
    """Test we can pop arbitrary elements from the pathspec."""
    sample = rdfvalue.RDFPathSpec(
        path="/", pathtype=rdfvalue.RDFPathSpec.Enum("OS"))

    for i in range(5):
      sample.Append(
          path=str(i), pathtype=rdfvalue.RDFPathSpec.Enum("OS"))

    self.assertEqual([x.path for x in sample],
                     list("/01234"))

    # Check we pop the right element.
    popped = sample.Pop(2)
    self.assertIsInstance(popped, rdfvalue.RDFPathSpec)
    self.assertEqual(popped.path, "1")
    self.assertEqual([x.path for x in sample],
                     list("/0234"))

    # The first element needs special treatment.
    self.assertEqual(sample.Pop(0).path, "/")
    self.assertEqual([x.path for x in sample],
                     list("0234"))

  def testRDFPathSpec(self):
    """Test that RDFPathSpec works."""
    # Make a template pathspec using a protobuf the hard way.
    pathspec_pb = jobs_pb2.Path(path="/", pathtype=1)
    pathspec_pb.nested_path.path = "foo"
    pathspec_pb.nested_path.pathtype = 2

    # Create a new RDFPathspec from scratch.
    pathspec = rdfvalue.RDFPathSpec()
    pathspec.path = "/"
    pathspec.pathtype = 1
    pathspec.Append(path="foo", pathtype=2)

    self.assertEqual(pathspec_pb.SerializeToString(),
                     pathspec.SerializeToString())

    # Create a new RDFPathspec from keywords.
    pathspec = rdfvalue.RDFPathSpec(path="/", pathtype=1)
    pathspec.Append(path="foo", pathtype=2)

    self.assertEqual(pathspec_pb.SerializeToString(),
                     pathspec.SerializeToString())

    # Check that copies are ok
    pathspec = pathspec.Copy()

    self.assertEqual(pathspec_pb.SerializeToString(),
                     pathspec.SerializeToString())

    # Accessors:
    self.assertEqual(pathspec.path, "/")
    self.assertEqual(pathspec.last.path, "foo")

    # Initialize from a protobuf.
    pathspec_pb_copy = jobs_pb2.Path()
    pathspec_pb_copy.CopyFrom(pathspec_pb)

    pathspec = rdfvalue.RDFPathSpec(pathspec_pb_copy)
    self.assertEqual(pathspec_pb.SerializeToString(),
                     pathspec.SerializeToString())

    # Modifying the protobuf in place. An RDFPathSpec which is instantiated
    # using a protobuf simply wraps it rather than making a copy. Any
    # modifications to the RDFPathSpec object are reflected in the underlying
    # protobuf.
    pathspec.first.path = "test"
    self.assertEqual(pathspec.path, pathspec_pb_copy.path)

    self.assertEqual(pathspec.last.path, "foo")

    # Test Pathspec iterator.
    self.assertEqual([x.path for x in pathspec], ["test", "foo"])

    # Length.
    self.assertEqual(len(pathspec), 2)

    pathspec = rdfvalue.RDFPathSpec(path="/foo", pathtype=1)
    pathspec.Append(path="/", pathtype=0)
    self.assertEqual(pathspec.Dirname().CollapsePath(), "/")
    pathspec.Append(path="sdasda", pathtype=0)
    self.assertEqual(pathspec.Dirname().CollapsePath(), "/foo")

    pathspec = rdfvalue.RDFPathSpec(path="/foo", pathtype=1)
    pathspec_base = rdfvalue.RDFPathSpec()
    pathspec_base.Append(pathspec)

    self.assertEqual(pathspec_base.CollapsePath(), "/foo")

    pathspec_base = rdfvalue.RDFPathSpec()
    pathspec_base.Insert(0, path="/foo", pathtype=1)

    self.assertEqual(pathspec_base.CollapsePath(), "/foo")

  def testUnicodePaths(self):
    """Test that we can manipulate paths in unicode."""
    sample = rdfvalue.RDFPathSpec(pathtype=1,
                                  path=u"/dev/c/msn升级程序[1].exe")

    # Ensure we can convert to a string.
    str(sample)
    unicode(sample)
