#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

# Copyright 2012 Google Inc. All Rights Reserved.
"""These are tests for the PathSpec implementation."""



from grr.lib import aff4
from grr.lib import rdfvalue
from grr.lib.rdfvalues import test_base
from grr.proto import jobs_pb2


class PathSpecTest(test_base.RDFProtoTestCase):
  """Test the PathSpec implementation."""

  rdfvalue_class = rdfvalue.PathSpec

  def CheckRDFValue(self, rdfproto, sample):
    """Check that the rdfproto is the same as the sample."""
    super(PathSpecTest, self).CheckRDFValue(rdfproto, sample)

    self.assertEqual(rdfproto.path, sample.path)
    self.assertEqual(rdfproto.pathtype, sample.pathtype)

  def GenerateSample(self, number=0):
    """Make a sample PathSpec instance."""
    return rdfvalue.PathSpec(path="/%s/" % number, pathtype=number)

  def testPop(self):
    """Test we can pop arbitrary elements from the pathspec."""
    sample = rdfvalue.PathSpec(
        path="/", pathtype=rdfvalue.PathSpec.PathType.OS)

    for i in range(5):
      sample.Append(
          path=str(i), pathtype=rdfvalue.PathSpec.PathType.OS)

    self.assertEqual([x.path for x in sample],
                     list("/01234"))

    # Check we pop the right element.
    popped = sample.Pop(2)
    self.assertIsInstance(popped, rdfvalue.PathSpec)
    self.assertEqual(popped.path, "1")
    self.assertEqual([x.path for x in sample],
                     list("/0234"))

    # The first element needs special treatment.
    self.assertEqual(sample.Pop(0).path, "/")
    self.assertEqual([x.path for x in sample],
                     list("0234"))

  def testPathSpec(self):
    """Test that PathSpec works."""
    # Make a template pathspec using a protobuf the hard way.
    pathspec_pb = jobs_pb2.PathSpec(path="/", pathtype=1)
    pathspec_pb.nested_path.path = "foo"
    pathspec_pb.nested_path.pathtype = 2

    # Create a new RDFPathspec from scratch.
    pathspec = rdfvalue.PathSpec()
    pathspec.path = "/"
    pathspec.pathtype = 1
    pathspec.Append(path="foo", pathtype=2)

    self.assertProtoEqual(pathspec_pb, pathspec)

    # Create a new RDFPathspec from keywords.
    pathspec = rdfvalue.PathSpec(path="/", pathtype=1)
    pathspec.Append(path="foo", pathtype=2)

    self.assertProtoEqual(pathspec_pb, pathspec)

    # Check that copies are ok
    pathspec = pathspec.Copy()

    self.assertProtoEqual(pathspec_pb, pathspec)

    # Accessors:
    self.assertEqual(pathspec.path, "/")
    self.assertEqual(pathspec.last.path, "foo")

    # Initialize from a protobuf.
    pathspec_pb_copy = jobs_pb2.PathSpec()
    pathspec_pb_copy.CopyFrom(pathspec_pb)

    pathspec = rdfvalue.PathSpec(pathspec_pb_copy)
    self.assertProtoEqual(pathspec_pb, pathspec)

    pathspec.first.path = "test"
    self.assertEqual(pathspec.last.path, "foo")

    # Test Pathspec iterator.
    self.assertEqual([x.path for x in pathspec], ["test", "foo"])

    # Length.
    self.assertEqual(len(pathspec), 2)

    pathspec = rdfvalue.PathSpec(path="/foo", pathtype=1)
    pathspec.Append(path="/", pathtype=0)
    self.assertEqual(pathspec.Dirname().CollapsePath(), "/")
    pathspec.Append(path="sdasda", pathtype=0)
    self.assertEqual(pathspec.Dirname().CollapsePath(), "/foo")

    pathspec = rdfvalue.PathSpec(path="/foo", pathtype=1)
    pathspec_base = rdfvalue.PathSpec()
    pathspec_base.Append(pathspec)

    self.assertEqual(pathspec_base.CollapsePath(), "/foo")

    pathspec_base = rdfvalue.PathSpec()
    pathspec_base.Insert(0, path="/foo", pathtype=1)

    self.assertEqual(pathspec_base.CollapsePath(), "/foo")

  def testUnicodePaths(self):
    """Test that we can manipulate paths in unicode."""
    sample = rdfvalue.PathSpec(pathtype=1,
                               path=u"/dev/c/msn升级程序[1].exe")

    # Ensure we can convert to a string.
    str(sample)
    unicode(sample)

  def testCopy(self):
    sample = rdfvalue.PathSpec(
        path="/", pathtype=rdfvalue.PathSpec.PathType.OS)
    sample.Append(path="foo", pathtype=rdfvalue.PathSpec.PathType.TSK)

    # Make a copy of the original and change it.
    sample_copy = sample.Copy()
    sample_copy.last.path = "bar"

    # This should not change the original.
    self.assertEqual(sample.last.path, "foo")


class GlobExpressionTest(test_base.RDFValueTestCase):
  rdfvalue_class = rdfvalue.GlobExpression

  USER_ACCOUNT = dict(
      username=u"user", full_name=u"John Smith",
      comment=u"This is a user", last_logon=10000,
      domain=u"Some domain name",
      homedir=u"/home/user",
      sid=u"some sid")

  def GenerateSample(self, number=0):
    return self.rdfvalue_class("/home/%%User.username%%/*" + str(number))

  def testClientInterpolation(self):
    client_id = "C.0000000000000001"

    fd = aff4.FACTORY.Create(client_id, "VFSGRRClient", token=self.token)
    users = fd.Schema.USER()

    # Add 2 users
    for i in range(2):
      account_info = self.USER_ACCOUNT.copy()
      account_info["username"] = "user%s" % i
      users.Append(**account_info)

    fd.Set(users)
    fd.Close()

    fd = aff4.FACTORY.Open(client_id, token=self.token)
    glob_expression = rdfvalue.GlobExpression(
        "/home/%%Users.username%%/.mozilla/")

    interpolated = sorted(glob_expression.InterpolateClientAttributes(
        client=fd))
    self.assertEqual(interpolated[0], "/home/user0/.mozilla/")
    self.assertEqual(interpolated[1], "/home/user1/.mozilla/")

  def testValidation(self):
    glob_expression = rdfvalue.GlobExpression(
        "/home/%%Users.username%%/**/.mozilla/")
    glob_expression.Validate()

    glob_expression = rdfvalue.GlobExpression(
        "/home/**/**")
    self.assertRaises(ValueError, glob_expression.Validate)

