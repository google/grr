#!/usr/bin/env python
# Lint as: python3
# -*- encoding: utf-8 -*-

# Copyright 2012 Google Inc. All Rights Reserved.
"""These are tests for the PathSpec implementation."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from absl import app

from grr_response_core.lib.rdfvalues import client as rdf_client
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

    reference_pathspec = rdf_paths.PathSpec.FromSerializedBytes(
        pathspec_pb.SerializeToString())

    # Create a new RDFPathspec from scratch.
    pathspec = rdf_paths.PathSpec()
    pathspec.path = "/"
    pathspec.pathtype = 1
    pathspec.Append(path="foo", pathtype=2)

    self.assertEqual(pathspec, reference_pathspec)

    # Create a new RDFPathspec from keywords.
    pathspec = rdf_paths.PathSpec(path="/", pathtype=1)
    pathspec.Append(path="foo", pathtype=2)

    self.assertEqual(pathspec, reference_pathspec)

    # Check that copies are ok
    pathspec = pathspec.Copy()

    self.assertEqual(pathspec, reference_pathspec)

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

  def testCopy(self):
    sample = rdf_paths.PathSpec(
        path="/", pathtype=rdf_paths.PathSpec.PathType.OS)
    sample.Append(path="foo", pathtype=rdf_paths.PathSpec.PathType.TSK)

    # Make a copy of the original and change it.
    sample_copy = sample.Copy()
    sample_copy.last.path = "bar"

    # This should not change the original.
    self.assertEqual(sample.last.path, "foo")

  def testOsConstructor(self):
    pathspec = rdf_paths.PathSpec.OS(path="foo")

    self.assertEqual(pathspec.path, "foo")
    self.assertEqual(pathspec.pathtype, rdf_paths.PathSpec.PathType.OS)

  def testTskConstructor(self):
    pathspec = rdf_paths.PathSpec.TSK(mount_point="C:\\")

    self.assertEqual(pathspec.mount_point, "C:\\")
    self.assertEqual(pathspec.pathtype, rdf_paths.PathSpec.PathType.TSK)

  def testNtfsConstructor(self):
    pathspec = rdf_paths.PathSpec.NTFS(mount_point="C:\\")

    self.assertEqual(pathspec.mount_point, "C:\\")
    self.assertEqual(pathspec.pathtype, rdf_paths.PathSpec.PathType.NTFS)

  def testRegistryConstructor(self):
    pathspec = rdf_paths.PathSpec.Registry(path="HKLM\\System\\foo\\bar")

    self.assertEqual(pathspec.path, "HKLM\\System\\foo\\bar")
    self.assertEqual(pathspec.pathtype, rdf_paths.PathSpec.PathType.REGISTRY)

  def testTempConstructor(self):
    pathspec = rdf_paths.PathSpec.Temp(is_virtualroot=True)

    self.assertTrue(pathspec.is_virtualroot)
    self.assertEqual(pathspec.pathtype, rdf_paths.PathSpec.PathType.TMPFILE)


class GlobExpressionTest(rdf_test_base.RDFValueTestMixin, test_lib.GRRBaseTest):
  rdfvalue_class = rdf_paths.GlobExpression

  def GenerateSample(self, number=0):
    return self.rdfvalue_class("/home/%%users.username%%/*{}".format(number))

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
        "/home/%%users.username%%/**/.mozilla/")
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

  def testGlobExpressionSplitsIntoExplainableComponents(self):
    kb = rdf_client.KnowledgeBase(users=[
        rdf_client.User(homedir="/home/foo"),
        rdf_client.User(homedir="/home/bar"),
        rdf_client.User(homedir="/home/baz"),
    ])

    # Test for preservation of **/ because it behaves different to **.
    ge = rdf_paths.GlobExpression("/foo/**/{bar,baz}/bar?/.*baz")
    components = ge.ExplainComponents(2, kb)
    self.assertEqual(
        [c.glob_expression for c in components],
        ["/foo/", "**/", "{bar,baz}", "/bar", "?", "/.", "*", "baz"])

    ge = rdf_paths.GlobExpression("/foo/**bar")
    components = ge.ExplainComponents(2, kb)
    self.assertEqual([c.glob_expression for c in components],
                     ["/foo/", "**", "bar"])

    ge = rdf_paths.GlobExpression("/foo/**10bar")
    components = ge.ExplainComponents(2, kb)
    self.assertEqual([c.glob_expression for c in components],
                     ["/foo/", "**10", "bar"])

    ge = rdf_paths.GlobExpression("/{foo,bar,baz}")
    components = ge.ExplainComponents(2, kb)
    self.assertEqual(components[1].examples, ["foo", "bar"])

    ge = rdf_paths.GlobExpression("%%users.homedir%%/foo")
    components = ge.ExplainComponents(2, kb)
    self.assertEqual([c.glob_expression for c in components],
                     ["%%users.homedir%%", "/foo"])
    self.assertEqual(components[0].examples, ["/home/foo", "/home/bar"])

  def _testAFF4Path_mountPointResolution(
      self, pathtype: rdf_paths.PathSpec.PathType) -> None:
    path = rdf_paths.PathSpec(
        path="\\\\.\\Volume{1234}\\",
        pathtype=rdf_paths.PathSpec.PathType.OS,
        mount_point="/c:/",
        nested_path=rdf_paths.PathSpec(
            path="/windows/",
            pathtype=pathtype,
        ))
    prefix = rdf_paths.PathSpec.AFF4_PREFIXES[pathtype]
    self.assertEqual(
        str(path.AFF4Path(rdf_client.ClientURN("C.0000000000000001"))),
        f"aff4:/C.0000000000000001{prefix}/\\\\.\\Volume{{1234}}\\/windows")

  def testAFF4Path_mountPointResolution_TSK(self):
    self._testAFF4Path_mountPointResolution(rdf_paths.PathSpec.PathType.TSK)

  def testAFF4Path_mountPointResolution_NTFS(self):
    self._testAFF4Path_mountPointResolution(rdf_paths.PathSpec.PathType.NTFS)


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
