#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

# Copyright 2012 Google Inc. All Rights Reserved.
"""These are tests for the PathSpec implementation."""



from grr.lib.rdfvalues import paths as rdf_paths
from grr.lib.rdfvalues import test_base
from grr.proto import jobs_pb2


class PathSpecTest(test_base.RDFProtoTestCase):
  """Test the PathSpec implementation."""

  rdfvalue_class = rdf_paths.PathSpec

  def CheckRDFValue(self, rdfproto, sample):
    """Check that the rdfproto is the same as the sample."""
    super(PathSpecTest, self).CheckRDFValue(rdfproto, sample)

    self.assertEqual(rdfproto.path, sample.path)
    self.assertEqual(rdfproto.pathtype, sample.pathtype)

  def GenerateSample(self, number=0):
    """Make a sample PathSpec instance."""
    return rdf_paths.PathSpec(path="/%s/" % number, pathtype=number)

  def testPop(self):
    """Test we can pop arbitrary elements from the pathspec."""
    sample = rdf_paths.PathSpec(path="/",
                                pathtype=rdf_paths.PathSpec.PathType.OS)

    for i in range(5):
      sample.Append(path=str(i), pathtype=rdf_paths.PathSpec.PathType.OS)

    self.assertEqual([x.path for x in sample], list("/01234"))

    # Check we pop the right element.
    popped = sample.Pop(2)
    self.assertIsInstance(popped, rdf_paths.PathSpec)
    self.assertEqual(popped.path, "1")
    self.assertEqual([x.path for x in sample], list("/0234"))

    # The first element needs special treatment.
    self.assertEqual(sample.Pop(0).path, "/")
    self.assertEqual([x.path for x in sample], list("0234"))

  def testPathSpec(self):
    """Test that PathSpec works."""
    # Make a template pathspec using a protobuf the hard way.
    pathspec_pb = jobs_pb2.PathSpec(path="/", pathtype=1)
    pathspec_pb.nested_path.path = "foo"
    pathspec_pb.nested_path.pathtype = 2

    reference_pathspec = rdf_paths.PathSpec(pathspec_pb.SerializeToString())

    # Create a new RDFPathspec from scratch.
    pathspec = rdf_paths.PathSpec()
    pathspec.path = "/"
    pathspec.pathtype = 1
    pathspec.Append(path="foo", pathtype=2)

    self.assertRDFValuesEqual(pathspec, reference_pathspec)

    # Create a new RDFPathspec from keywords.
    pathspec = rdf_paths.PathSpec(path="/", pathtype=1)
    pathspec.Append(path="foo", pathtype=2)

    self.assertRDFValuesEqual(pathspec, reference_pathspec)

    # Check that copies are ok
    pathspec = pathspec.Copy()

    self.assertRDFValuesEqual(pathspec, reference_pathspec)

    # Accessors:
    self.assertEqual(pathspec.path, "/")
    self.assertEqual(pathspec.last.path, "foo")

    # Initialize from a protobuf.
    pathspec_pb_copy = jobs_pb2.PathSpec()
    pathspec_pb_copy.CopyFrom(pathspec_pb)

    pathspec = rdf_paths.PathSpec(pathspec_pb_copy)
    self.assertRDFValuesEqual(pathspec, reference_pathspec)

    pathspec.first.path = "test"
    self.assertEqual(pathspec.last.path, "foo")

    # Test Pathspec iterator.
    self.assertEqual([x.path for x in pathspec], ["test", "foo"])

    # Length.
    self.assertEqual(len(pathspec), 2)

    pathspec = rdf_paths.PathSpec(path="/foo", pathtype=1)
    pathspec.Append(path="/", pathtype=0)
    self.assertEqual(pathspec.Dirname().CollapsePath(), "/")
    pathspec.Append(path="sdasda", pathtype=0)
    self.assertEqual(pathspec.Dirname().CollapsePath(), "/foo")

    pathspec = rdf_paths.PathSpec(path="/foo", pathtype=1)
    pathspec_base = rdf_paths.PathSpec()
    pathspec_base.Append(pathspec)

    self.assertEqual(pathspec_base.CollapsePath(), "/foo")

    pathspec_base = rdf_paths.PathSpec()
    pathspec_base.Insert(0, path="/foo", pathtype=1)

    self.assertEqual(pathspec_base.CollapsePath(), "/foo")

  def testUnicodePaths(self):
    """Test that we can manipulate paths in unicode."""
    sample = rdf_paths.PathSpec(pathtype=1, path=u"/dev/c/msn升级程序[1].exe")

    # Ensure we can convert to a string.
    str(sample)
    unicode(sample)

  def testCopy(self):
    sample = rdf_paths.PathSpec(path="/",
                                pathtype=rdf_paths.PathSpec.PathType.OS)
    sample.Append(path="foo", pathtype=rdf_paths.PathSpec.PathType.TSK)

    # Make a copy of the original and change it.
    sample_copy = sample.Copy()
    sample_copy.last.path = "bar"

    # This should not change the original.
    self.assertEqual(sample.last.path, "foo")


class GlobExpressionTest(test_base.RDFValueTestCase):
  rdfvalue_class = rdf_paths.GlobExpression

  USER_ACCOUNT = dict(username=u"user",
                      full_name=u"John Smith",
                      comment=u"This is a user",
                      last_logon=10000,
                      domain=u"Some domain name",
                      homedir=u"/home/user",
                      sid=u"some sid")

  def GenerateSample(self, number=0):
    return self.rdfvalue_class("/home/%%User.username%%/*" + str(number))

  def testGroupingInterpolation(self):
    glob_expression = rdf_paths.GlobExpression()

    interpolated = glob_expression.InterpolateGrouping("/home/*.{sh,deb}")
    self.assertItemsEqual(interpolated, [u"/home/*.deb", u"/home/*.sh"])
    interpolated = glob_expression.InterpolateGrouping("/home/*.{sh, deb}")
    self.assertItemsEqual(interpolated, [u"/home/*. deb", u"/home/*.sh"])
    interpolated = glob_expression.InterpolateGrouping(
        "HKEY_CLASSES_ROOT/CLSID/{16d12736-7a9e-4765-bec6-f301d679caaa}")
    self.assertItemsEqual(interpolated, [
        u"HKEY_CLASSES_ROOT/CLSID/{16d12736-7a9e-4765-bec6-f301d679caaa}"
    ])

  def testValidation(self):
    glob_expression = rdf_paths.GlobExpression(
        "/home/%%Users.username%%/**/.mozilla/")
    glob_expression.Validate()

    glob_expression = rdf_paths.GlobExpression("/home/**/**")
    self.assertRaises(ValueError, glob_expression.Validate)
