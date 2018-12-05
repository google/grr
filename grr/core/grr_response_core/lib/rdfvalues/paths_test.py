#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

# Copyright 2012 Google Inc. All Rights Reserved.
"""These are tests for the PathSpec implementation."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from builtins import range  # pylint: disable=redefined-builtin

from grr_response_core.lib import flags
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import test_base as rdf_test_base
from grr_response_proto import jobs_pb2
from grr.test_lib import test_lib


class PathSpecTest(rdf_test_base.RDFProtoTestMixin, test_lib.GRRBaseTest):
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
    sample = rdf_paths.PathSpec(
        path="/", pathtype=rdf_paths.PathSpec.PathType.OS)

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

    reference_pathspec = rdf_paths.PathSpec.FromSerializedString(
        pathspec_pb.SerializeToString())

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

    pathspec.first.path = "test"
    self.assertEqual(pathspec.last.path, "foo")

    # Test Pathspec iterator.
    self.assertEqual([x.path for x in pathspec], ["test", "foo"])

    # Length.
    self.assertLen(pathspec, 2)

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
    sample = rdf_paths.PathSpec(
        path="/", pathtype=rdf_paths.PathSpec.PathType.OS)
    sample.Append(path="foo", pathtype=rdf_paths.PathSpec.PathType.TSK)

    # Make a copy of the original and change it.
    sample_copy = sample.Copy()
    sample_copy.last.path = "bar"

    # This should not change the original.
    self.assertEqual(sample.last.path, "foo")


class GlobExpressionTest(rdf_test_base.RDFValueTestMixin, test_lib.GRRBaseTest):
  rdfvalue_class = rdf_paths.GlobExpression

  USER_ACCOUNT = dict(
      username=u"user",
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
    self.assertCountEqual(interpolated, [u"/home/*.deb", u"/home/*.sh"])
    interpolated = glob_expression.InterpolateGrouping("/home/*.{sh, deb}")
    self.assertCountEqual(interpolated, [u"/home/*. deb", u"/home/*.sh"])
    interpolated = glob_expression.InterpolateGrouping(
        "HKEY_CLASSES_ROOT/CLSID/{16d12736-7a9e-4765-bec6-f301d679caaa}")
    self.assertCountEqual(
        interpolated,
        [u"HKEY_CLASSES_ROOT/CLSID/{16d12736-7a9e-4765-bec6-f301d679caaa}"])

  def testValidation(self):
    glob_expression = rdf_paths.GlobExpression(
        "/home/%%Users.username%%/**/.mozilla/")
    glob_expression.Validate()

    glob_expression = rdf_paths.GlobExpression("/home/**/**")
    self.assertRaises(ValueError, glob_expression.Validate)

  def testRegExIsCorrectForGlobWithoutStars(self):
    glob_expression = rdf_paths.GlobExpression("/foo/bar/blah.txt")
    regex = glob_expression.AsRegEx()

    self.assertTrue(regex.Match("/foo/bar/blah.txt"))
    self.assertFalse(regex.Match("/foo/bar/blah2.txt"))
    self.assertFalse(regex.Match("/some/foo/bar/blah2.txt"))
    self.assertFalse(regex.Match("/some/foo/bar/blah2.txt/other"))

  def testRegExIsCorrectForGlobWithQuestion(self):
    glob_expression = rdf_paths.GlobExpression("/foo/bar/???.txt")
    regex = glob_expression.AsRegEx()

    self.assertTrue(regex.Match("/foo/bar/bla.txt"))
    self.assertFalse(regex.Match("/foo/bar/blah.txt"))

  def testRegExIsCorrectForGlobWithGrouping(self):
    glob_expression = rdf_paths.GlobExpression("/foo/{bar,other}/*{.txt,.exe}")
    regex = glob_expression.AsRegEx()

    self.assertTrue(regex.Match("/foo/bar/blah.txt"))
    self.assertTrue(regex.Match("/foo/other/blah2.txt"))
    self.assertTrue(regex.Match("/foo/bar/blah.exe"))
    self.assertTrue(regex.Match("/foo/other/blah2.exe"))

    self.assertFalse(regex.Match("/foo/other2/blah.txt"))
    self.assertFalse(regex.Match("/foo/bar/blah.com"))

  def testRegExIsCorrectForGlobWithSingleStar(self):
    glob_expression = rdf_paths.GlobExpression("/foo/bar/*.txt")
    regex = glob_expression.AsRegEx()

    self.assertTrue(regex.Match("/foo/bar/blah.txt"))

    self.assertFalse(regex.Match("/foo/bar/blah.plist"))
    self.assertFalse(regex.Match("/foo/bar/blah/blah.txt"))
    self.assertFalse(regex.Match("/foo/blah1/blah2/bar/blah.txt"))

  def testRegExIsCorrectForGlobWithTwoStars(self):
    glob_expression = rdf_paths.GlobExpression("/foo/**/bar.txt")
    regex = glob_expression.AsRegEx()

    self.assertTrue(regex.Match("/foo/bar.txt"))
    self.assertTrue(regex.Match("/foo/blah/bar.txt"))
    self.assertTrue(regex.Match("/foo/blah1/blah2/bar.txt"))

    self.assertFalse(regex.Match("/foo/bar.plist"))
    self.assertFalse(regex.Match("/foo/blah/bar.txt/res"))
    self.assertFalse(regex.Match("/foo/blah1/blah2/bar.txt2"))

  def testRegExIsCorrectForComplexGlob(self):
    glob_expression = rdf_paths.GlobExpression("/foo/**/bar?/*{.txt,.exe}")
    regex = glob_expression.AsRegEx()

    self.assertTrue(regex.Match("/foo/bar1/blah.txt"))
    self.assertTrue(regex.Match("/foo/bar2/blah.exe"))
    self.assertTrue(regex.Match("/foo/c1/c2/c3/bar1/blah.txt"))
    self.assertTrue(regex.Match("/foo/c1/c2/c3/bar2/blah.exe"))

    self.assertFalse(regex.Match("/foo/bar/blah.txt"))
    self.assertFalse(regex.Match("/foo/bar2/blah.com"))
    self.assertFalse(regex.Match("/foo/c1/c2/c3/bar1/blah.txt/res.txt"))
    self.assertFalse(regex.Match("/foo/c1/c2/c3/bar2/blah.exe/res.exe"))

  def testRegExIsCaseInsensitive(self):
    glob_expression = rdf_paths.GlobExpression("/foo/**/bar?/*{.txt,.exe}")
    regex = glob_expression.AsRegEx()

    self.assertTrue(regex.Match("/foo/bar1/blah.txt"))
    self.assertTrue(regex.Match("/foO/bAr1/blah.txt"))
    self.assertTrue(regex.Match("/foo/bar1/blah.TXT"))

    self.assertFalse(regex.Match("/foo/bar2/blah.com"))
    self.assertFalse(regex.Match("/foO/bAr2/blah.com"))
    self.assertFalse(regex.Match("/foo/bar2/blah.COM"))


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
