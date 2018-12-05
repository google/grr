#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import io
import os
import shutil
import unittest


from absl.testing import absltest
from builtins import zip  # pylint: disable=redefined-builtin

from grr_response_client.client_actions.file_finder_utils import globbing
from grr_response_core.lib import flags
from grr.test_lib import temp
from grr.test_lib import test_lib

# TODO(hanuszczak): Consider refactoring these tests with `pyfakefs`.


class DirHierarchyTestMixin(object):

  def setUp(self):
    super(DirHierarchyTestMixin, self).setUp()
    self.tempdir = temp.TempDirPath()

  def tearDown(self):
    super(DirHierarchyTestMixin, self).tearDown()
    shutil.rmtree(self.tempdir)

  def Path(self, *components):
    return os.path.join(self.tempdir, *components)

  def Touch(self, *components):
    filepath = self.Path(*components)
    dirpath = os.path.dirname(filepath)

    try:
      if not os.path.exists(dirpath):
        os.makedirs(dirpath)
      with io.open(filepath, "a"):
        pass
    except UnicodeEncodeError:
      # TODO(hanuszczak): Make sure that Python 3 also throws the same error
      # in case of unsupported unicodes in the filesystem. In general this
      # exception being thrown feels very fishy.
      raise unittest.SkipTest("Unicode not supported by the filesystem")


class RecursiveComponentTest(DirHierarchyTestMixin, absltest.TestCase):

  def testSimple(self):
    self.Touch("foo", "0")
    self.Touch("foo", "1")
    self.Touch("foo", "bar", "0")
    self.Touch("baz", "0")
    self.Touch("baz", "1")

    component = globbing.RecursiveComponent()

    results = list(component.Generate(self.Path()))
    self.assertCountEqual(results, [
        self.Path("foo"),
        self.Path("foo", "0"),
        self.Path("foo", "1"),
        self.Path("foo", "bar"),
        self.Path("foo", "bar", "0"),
        self.Path("baz"),
        self.Path("baz", "0"),
        self.Path("baz", "1"),
    ])

    results = list(component.Generate(self.Path("foo")))
    self.assertCountEqual(results, [
        self.Path("foo", "0"),
        self.Path("foo", "1"),
        self.Path("foo", "bar"),
        self.Path("foo", "bar", "0"),
    ])

    results = list(component.Generate(self.Path("baz")))
    self.assertCountEqual(results, [
        self.Path("baz", "0"),
        self.Path("baz", "1"),
    ])

    results = list(component.Generate(self.Path("foo", "bar")))
    self.assertCountEqual(results, [
        self.Path("foo", "bar", "0"),
    ])

  def testMaxDepth(self):
    self.Touch("foo", "0")
    self.Touch("foo", "1")
    self.Touch("foo", "bar", "0")
    self.Touch("foo", "bar", "baz", "0")

    component = globbing.RecursiveComponent(max_depth=3)

    results = list(component.Generate(self.Path()))

    # Files at level lesser than 3 should be included.
    self.assertIn(self.Path("foo"), results)
    self.assertIn(self.Path("foo", "0"), results)
    self.assertIn(self.Path("foo", "1"), results)
    self.assertIn(self.Path("foo", "bar"), results)

    # Files at level equal to 3 should be included.
    self.assertIn(self.Path("foo", "bar", "0"), results)
    self.assertIn(self.Path("foo", "bar", "baz"), results)

    # Files at level bigger that 3 should not be included.
    self.assertNotIn(self.Path("foo", "bar", "baz", "0"), results)

  def testIgnore(self):
    self.Touch("foo", "0")
    self.Touch("foo", "1")
    self.Touch("foo", "bar", "0")
    self.Touch("bar", "0")
    self.Touch("bar", "quux", "0")
    self.Touch("bar", "quux", "1")
    self.Touch("baz", "0")
    self.Touch("baz", "1")
    self.Touch("baz", "quux", "0")

    opts = globbing.PathOpts(recursion_blacklist=[
        self.Path("foo"),
        self.Path("bar", "quux"),
    ])
    component = globbing.RecursiveComponent(opts=opts)

    results = list(component.Generate(self.Path()))

    # Recursion should not visit into the blacklisted folders.
    self.assertNotIn(self.Path("foo", "0"), results)
    self.assertNotIn(self.Path("foo", "1"), results)
    self.assertNotIn(self.Path("bar", "quux", "0"), results)
    self.assertNotIn(self.Path("bar", "quux", "1"), results)

    # Blacklisted folders themselves should appear in the results.
    self.assertIn(self.Path("foo"), results)
    self.assertIn(self.Path("bar", "quux"), results)

    # Recursion should visit not blacklisted folders.
    self.assertIn(self.Path("baz"), results)
    self.assertIn(self.Path("baz", "0"), results)
    self.assertIn(self.Path("baz", "1"), results)
    self.assertIn(self.Path("baz", "quux"), results)
    self.assertIn(self.Path("baz", "quux", "0"), results)

  def testFollowLinks(self):
    self.Touch("foo", "0")
    self.Touch("foo", "bar", "0")
    self.Touch("foo", "baz", "0")
    self.Touch("foo", "baz", "1")
    self.Touch("quux", "0")
    self.Touch("norf", "0")
    os.symlink(self.Path("foo", "bar"), self.Path("quux", "bar"))
    os.symlink(self.Path("foo", "baz"), self.Path("quux", "baz"))
    os.symlink(self.Path("quux"), self.Path("norf", "quux"))

    opts = globbing.PathOpts(follow_links=True)
    component = globbing.RecursiveComponent(opts=opts)

    # It should resolve two links and recur to linked directories.
    results = list(component.Generate(self.Path("quux")))
    self.assertCountEqual(results, [
        self.Path("quux", "0"),
        self.Path("quux", "bar"),
        self.Path("quux", "bar", "0"),
        self.Path("quux", "baz"),
        self.Path("quux", "baz", "0"),
        self.Path("quux", "baz", "1"),
    ])

    # It should resolve symlinks recursively.
    results = list(component.Generate(self.Path("norf")))
    self.assertCountEqual(results, [
        self.Path("norf", "0"),
        self.Path("norf", "quux"),
        self.Path("norf", "quux", "0"),
        self.Path("norf", "quux", "bar"),
        self.Path("norf", "quux", "bar", "0"),
        self.Path("norf", "quux", "baz"),
        self.Path("norf", "quux", "baz", "0"),
        self.Path("norf", "quux", "baz", "1"),
    ])

    opts = globbing.PathOpts(follow_links=False)
    component = globbing.RecursiveComponent(opts=opts)

    # It should list symlinks but should not recur to linked directories.
    results = list(component.Generate(self.Path()))
    self.assertCountEqual(results, [
        self.Path("foo"),
        self.Path("foo", "0"),
        self.Path("foo", "bar"),
        self.Path("foo", "bar", "0"),
        self.Path("foo", "baz"),
        self.Path("foo", "baz", "0"),
        self.Path("foo", "baz", "1"),
        self.Path("quux"),
        self.Path("quux", "0"),
        self.Path("quux", "bar"),
        self.Path("quux", "baz"),
        self.Path("norf"),
        self.Path("norf", "0"),
        self.Path("norf", "quux"),
    ])

  def testInvalidDirpath(self):
    component = globbing.RecursiveComponent()

    results = list(component.Generate("/foo/bar/baz"))
    self.assertCountEqual(results, [])


class GlobComponentTest(DirHierarchyTestMixin, absltest.TestCase):

  def testLiterals(self):
    self.Touch("foo")
    self.Touch("bar")
    self.Touch("baz")

    component = globbing.GlobComponent("foo")

    results = list(component.Generate(self.Path()))
    self.assertCountEqual(results, [
        self.Path("foo"),
    ])

    component = globbing.GlobComponent("bar")

    results = list(component.Generate(self.Path()))
    self.assertCountEqual(results, [
        self.Path("bar"),
    ])

  def testStar(self):
    self.Touch("foo")
    self.Touch("bar")
    self.Touch("baz")
    self.Touch("quux")

    component = globbing.GlobComponent("*")

    results = list(component.Generate(self.Path()))
    self.assertCountEqual(results, [
        self.Path("foo"),
        self.Path("bar"),
        self.Path("baz"),
        self.Path("quux"),
    ])

    component = globbing.GlobComponent("ba*")

    results = list(component.Generate(self.Path()))
    self.assertCountEqual(results, [
        self.Path("bar"),
        self.Path("baz"),
    ])

  def testQuestionmark(self):
    self.Touch("foo")
    self.Touch("bar")
    self.Touch("baz")
    self.Touch("barg")

    component = globbing.GlobComponent("ba?")

    results = list(component.Generate(self.Path()))
    self.assertCountEqual(results, [
        self.Path("bar"),
        self.Path("baz"),
    ])

  def testSimpleClass(self):
    self.Touch("foo")
    self.Touch("bar")
    self.Touch("baz")
    self.Touch("baf")

    component = globbing.GlobComponent("ba[rz]")

    results = list(component.Generate(self.Path()))
    self.assertCountEqual(results, [
        self.Path("baz"),
        self.Path("bar"),
    ])

  def testRangeClass(self):
    self.Touch("foo")
    self.Touch("8AR")
    self.Touch("bar")
    self.Touch("4815162342")
    self.Touch("quux42")

    component = globbing.GlobComponent("[a-z]*")

    results = list(component.Generate(self.Path()))
    self.assertCountEqual(results, [
        self.Path("foo"),
        self.Path("bar"),
        self.Path("quux42"),
    ])

    component = globbing.GlobComponent("[0-9]*")

    results = list(component.Generate(self.Path()))
    self.assertCountEqual(results, [
        self.Path("8AR"),
        self.Path("4815162342"),
    ])

    component = globbing.GlobComponent("*[0-9]")

    results = list(component.Generate(self.Path()))
    self.assertCountEqual(results, [
        self.Path("4815162342"),
        self.Path("quux42"),
    ])

  def testMultiRangeClass(self):
    self.Touch("f00")
    self.Touch("b4R")
    self.Touch("8az")
    self.Touch("quux")

    component = globbing.GlobComponent("[a-z][a-z0-9]*")

    results = list(component.Generate(self.Path()))
    self.assertCountEqual(results, [
        self.Path("f00"),
        self.Path("b4R"),
        self.Path("quux"),
    ])

  def testComplementationClass(self):
    self.Touch("foo")
    self.Touch("bar")
    self.Touch("123")

    component = globbing.GlobComponent("*[!0-9]*")

    results = list(component.Generate(self.Path()))
    self.assertCountEqual(results, [
        self.Path("foo"),
        self.Path("bar"),
    ])

  def testCornerCases(self):
    self.Touch("[")
    self.Touch("-")
    self.Touch("]")
    self.Touch("!")
    self.Touch("*")
    self.Touch("?")
    self.Touch("foo")

    component = globbing.GlobComponent("[][-]")

    results = list(component.Generate(self.Path()))
    self.assertCountEqual(results, [
        self.Path("["),
        self.Path("-"),
        self.Path("]"),
    ])

    component = globbing.GlobComponent("[!]f-]*")

    results = list(component.Generate(self.Path()))
    self.assertCountEqual(results, [
        self.Path("["),
        self.Path("*"),
        self.Path("!"),
        self.Path("?"),
    ])

    component = globbing.GlobComponent("[*?]")

    results = list(component.Generate(self.Path()))
    self.assertCountEqual(results, [
        self.Path("*"),
        self.Path("?"),
    ])

  def testWhitespace(self):
    self.Touch("foo bar")
    self.Touch("   ")
    self.Touch("quux")

    component = globbing.GlobComponent("* *")

    results = list(component.Generate(self.Path()))
    self.assertCountEqual(results, [
        self.Path("foo bar"),
        self.Path("   "),
    ])

  def testCaseInsensivity(self):
    self.Touch("foo")
    self.Touch("BAR")
    self.Touch("BaZ")
    self.Touch("qUuX")

    component = globbing.GlobComponent("b*")
    results = list(component.Generate(self.Path()))
    self.assertCountEqual(results, [
        self.Path("BAR"),
        self.Path("BaZ"),
    ])

    component = globbing.GlobComponent("quux")
    results = list(component.Generate(self.Path()))
    self.assertCountEqual(results, [
        self.Path("qUuX"),
    ])

    component = globbing.GlobComponent("FoO")
    results = list(component.Generate(self.Path()))
    self.assertCountEqual(results, [
        self.Path("foo"),
    ])

  def testUnicodeGlobbing(self):
    self.Touch("ścieżka")
    self.Touch("dróżka")

    results = list(globbing.GlobComponent("ścieżka").Generate(self.Path()))
    self.assertCountEqual(results, [
        self.Path("ścieżka"),
    ])

    results = list(globbing.GlobComponent("dróżka").Generate(self.Path()))
    self.assertCountEqual(results, [
        self.Path("dróżka"),
    ])

    results = list(globbing.GlobComponent("*żka").Generate(self.Path()))
    self.assertCountEqual(results, [
        self.Path("ścieżka"),
        self.Path("dróżka"),
    ])

  def testUnicodeSubfolderGlobbing(self):
    self.Touch("zbiór", "podścieżka")
    self.Touch("zbiór", "poddróżka")

    results = list(globbing.GlobComponent("*").Generate(self.Path("zbiór")))
    self.assertCountEqual(results, [
        self.Path("zbiór", "podścieżka"),
        self.Path("zbiór", "poddróżka"),
    ])


class CurrentComponentTest(DirHierarchyTestMixin, absltest.TestCase):

  def testSimple(self):
    self.Touch("foo", "bar", "0")
    self.Touch("foo", "baz", "0")

    component = globbing.CurrentComponent()

    results = list(component.Generate(self.Path("foo")))
    self.assertCountEqual(results, [self.Path("foo")])

    results = list(component.Generate(self.Path("foo", "bar")))
    self.assertCountEqual(results, [self.Path("foo", "bar")])

    results = list(component.Generate(self.Path("foo", "baz")))
    self.assertCountEqual(results, [self.Path("foo", "baz")])


class ParentComponentTest(DirHierarchyTestMixin, absltest.TestCase):

  def testSimple(self):
    self.Touch("foo", "0")
    self.Touch("foo", "bar", "0")
    self.Touch("foo", "bar", "baz", "0")

    component = globbing.ParentComponent()

    results = list(component.Generate(self.Path("foo")))
    self.assertCountEqual(results, [self.Path()])

    results = list(component.Generate(self.Path("foo", "bar")))
    self.assertCountEqual(results, [self.Path("foo")])

    results = list(component.Generate(self.Path("foo", "bar", "baz")))
    self.assertCountEqual(results, [self.Path("foo", "bar")])


class ParsePathItemTest(absltest.TestCase):

  def testRecursive(self):
    component = globbing.ParsePathItem("**")
    self.assertIsInstance(component, globbing.RecursiveComponent)
    self.assertEqual(component.max_depth, 3)

  def testRecursiveWithDepth(self):
    component = globbing.ParsePathItem("**42")
    self.assertIsInstance(component, globbing.RecursiveComponent)
    self.assertEqual(component.max_depth, 42)

  def testGlob(self):
    component = globbing.ParsePathItem("foo*")
    self.assertIsInstance(component, globbing.GlobComponent)

    component = globbing.ParsePathItem("*")
    self.assertIsInstance(component, globbing.GlobComponent)

    component = globbing.ParsePathItem("foo ba?")
    self.assertIsInstance(component, globbing.GlobComponent)

  def testCurrent(self):
    component = globbing.ParsePathItem(os.path.curdir)
    self.assertIsInstance(component, globbing.CurrentComponent)

  def testParent(self):
    component = globbing.ParsePathItem(os.path.pardir)
    self.assertIsInstance(component, globbing.ParentComponent)

  def testMalformed(self):
    with self.assertRaises(ValueError):
      globbing.ParsePathItem("foo**")

    with self.assertRaises(ValueError):
      globbing.ParsePathItem("**10bar")


class ParsePathTest(absltest.TestCase):

  def assertAreInstances(self, instances, classes):
    for instance, clazz in zip(instances, classes):
      self.assertIsInstance(instance, clazz)
    self.assertLen(instances, len(classes))

  def testSimple(self):
    path = os.path.join("foo", "**", "ba*")

    components = list(globbing.ParsePath(path))
    self.assertAreInstances(components, [
        globbing.GlobComponent,
        globbing.RecursiveComponent,
        globbing.GlobComponent,
    ])

    path = os.path.join("foo", os.path.curdir, "bar", "baz", os.path.pardir)

    components = list(globbing.ParsePath(path))
    self.assertAreInstances(components, [
        globbing.GlobComponent,
        globbing.CurrentComponent,
        globbing.GlobComponent,
        globbing.GlobComponent,
        globbing.ParentComponent,
    ])

  def testMultiRecursive(self):
    path = os.path.join("foo", "**", "bar", "**", "baz")

    with self.assertRaises(ValueError):
      list(globbing.ParsePath(path))


class ExpandGroupsTest(absltest.TestCase):

  def testSimple(self):
    path = "fooba{r,z}"

    results = list(globbing.ExpandGroups(path))
    self.assertCountEqual(results, [
        "foobar",
        "foobaz",
    ])

  def testMultiple(self):
    path = os.path.join("f{o,0}o{bar,baz}", "{quux,norf}")

    results = list(globbing.ExpandGroups(path))
    self.assertCountEqual(results, [
        os.path.join("foobar", "quux"),
        os.path.join("foobar", "norf"),
        os.path.join("foobaz", "quux"),
        os.path.join("foobaz", "norf"),
        os.path.join("f0obar", "quux"),
        os.path.join("f0obar", "norf"),
        os.path.join("f0obaz", "quux"),
        os.path.join("f0obaz", "norf"),
    ])

  def testMany(self):
    path = os.path.join("foo{bar,baz,quux,norf}thud")

    results = list(globbing.ExpandGroups(path))
    self.assertCountEqual(results, [
        os.path.join("foobarthud"),
        os.path.join("foobazthud"),
        os.path.join("fooquuxthud"),
        os.path.join("foonorfthud"),
    ])

  def testEmpty(self):
    path = os.path.join("foo{}bar")

    results = list(globbing.ExpandGroups(path))
    self.assertCountEqual(results, ["foo{}bar"])

  def testSingleton(self):
    path = os.path.join("foo{bar}baz")

    results = list(globbing.ExpandGroups(path))
    self.assertCountEqual(results, ["foo{bar}baz"])

  def testUnclosed(self):
    path = os.path.join("foo{bar")

    results = list(globbing.ExpandGroups(path))
    self.assertCountEqual(results, ["foo{bar"])

    path = os.path.join("foo}bar")

    results = list(globbing.ExpandGroups(path))
    self.assertCountEqual(results, ["foo}bar"])

  def testEscaped(self):
    path = os.path.join("foo\\{baz}bar")

    results = list(globbing.ExpandGroups(path))
    self.assertCountEqual(results, ["foo\\{baz}bar"])

  def testNoGroup(self):
    path = os.path.join("foobarbaz")

    results = list(globbing.ExpandGroups(path))
    self.assertCountEqual(results, ["foobarbaz"])


class ExpandGlobsTest(DirHierarchyTestMixin, absltest.TestCase):

  def testWildcards(self):
    self.Touch("foo", "bar", "0")
    self.Touch("foo", "baz", "1")
    self.Touch("foo", "norf", "0")
    self.Touch("quux", "bar", "0")
    self.Touch("quux", "baz", "0")
    self.Touch("quux", "norf", "0")

    path = self.Path("*", "ba?", "0")

    results = list(globbing.ExpandGlobs(path))
    self.assertCountEqual(results, [
        self.Path("foo", "bar", "0"),
        self.Path("quux", "bar", "0"),
        self.Path("quux", "baz", "0"),
    ])

  def testRecursion(self):
    self.Touch("foo", "bar", "baz", "0")
    self.Touch("foo", "bar", "0")
    self.Touch("foo", "quux", "0")
    self.Touch("foo", "quux", "1")

    path = self.Path("foo", "**", "0")

    results = list(globbing.ExpandGlobs(path))
    self.assertCountEqual(results, [
        self.Path("foo", "bar", "baz", "0"),
        self.Path("foo", "bar", "0"),
        self.Path("foo", "quux", "0"),
    ])

  def testMixed(self):
    self.Touch("foo", "bar", "0")
    self.Touch("norf", "bar", "0")
    self.Touch("norf", "baz", "0")
    self.Touch("norf", "baz", "1")
    self.Touch("norf", "baz", "7")
    self.Touch("quux", "bar", "0")
    self.Touch("quux", "baz", "1")
    self.Touch("quux", "baz", "2")

    path = self.Path("**", "ba?", "[0-2]")

    results = list(globbing.ExpandGlobs(path))
    self.assertCountEqual(results, [
        self.Path("foo", "bar", "0"),
        self.Path("norf", "bar", "0"),
        self.Path("norf", "baz", "0"),
        self.Path("norf", "baz", "1"),
        self.Path("quux", "bar", "0"),
        self.Path("quux", "baz", "1"),
        self.Path("quux", "baz", "2"),
    ])

  def testEmpty(self):
    with self.assertRaises(ValueError):
      list(globbing.ExpandGlobs(""))

  def testRelative(self):
    with self.assertRaises(ValueError):
      list(globbing.ExpandGlobs(os.path.join("foo", "bar")))

  def testCurrent(self):
    self.Touch("foo", "bar", "0")
    self.Touch("foo", "bar", "1")
    self.Touch("quux", "bar", "0")

    path = self.Path("foo", os.path.curdir, "bar", "*")

    results = list(globbing.ExpandGlobs(path))
    self.assertCountEqual(results, [
        self.Path("foo", "bar", "0"),
        self.Path("foo", "bar", "1"),
    ])

    path = self.Path(os.path.curdir, "*", "bar", "0")

    results = list(globbing.ExpandGlobs(path))
    self.assertCountEqual(results, [
        self.Path("foo", "bar", "0"),
        self.Path("quux", "bar", "0"),
    ])

  def testParent(self):
    self.Touch("foo", "0")
    self.Touch("foo", "1")
    self.Touch("foo", "bar", "0")
    self.Touch("bar", "0")

    path = self.Path("foo", "*")

    results = list(globbing.ExpandGlobs(path))
    self.assertCountEqual(results, [
        self.Path("foo", "0"),
        self.Path("foo", "1"),
        self.Path("foo", "bar"),
    ])

    path = self.Path("foo", os.path.pardir, "*")

    results = list(globbing.ExpandGlobs(path))
    self.assertCountEqual(results, [
        self.Path("foo"),
        self.Path("bar"),
    ])


class ExpandPathTest(DirHierarchyTestMixin, absltest.TestCase):

  def testGlobAndGroup(self):
    self.Touch("foo", "bar", "0")
    self.Touch("foo", "bar", "1")
    self.Touch("foo", "baz", "0")
    self.Touch("foo", "baz", "1")
    self.Touch("foo", "quux", "0")
    self.Touch("foo", "quux", "1")

    path = self.Path("foo/ba{r,z}/*")
    results = list(globbing.ExpandPath(path))
    self.assertCountEqual(results, [
        self.Path("foo", "bar", "0"),
        self.Path("foo", "bar", "1"),
        self.Path("foo", "baz", "0"),
        self.Path("foo", "baz", "1"),
    ])

    path = self.Path("foo/ba*/{0,1}")
    results = list(globbing.ExpandPath(path))
    self.assertCountEqual(results, [
        self.Path("foo", "bar", "0"),
        self.Path("foo", "bar", "1"),
        self.Path("foo", "baz", "0"),
        self.Path("foo", "baz", "1"),
    ])

  def testRecursiveAndGroup(self):
    self.Touch("foo", "0")
    self.Touch("foo", "1")
    self.Touch("foo", "bar", "0")
    self.Touch("foo", "baz", "quux", "0")

    path = self.Path("foo/**")
    results = list(globbing.ExpandPath(path))
    self.assertCountEqual(results, [
        self.Path("foo", "0"),
        self.Path("foo", "1"),
        self.Path("foo", "bar"),
        self.Path("foo", "baz"),
        self.Path("foo", "bar", "0"),
        self.Path("foo", "baz", "quux"),
        self.Path("foo", "baz", "quux", "0"),
    ])

    path = self.Path("foo/{.,**}")
    results = list(globbing.ExpandPath(path))
    self.assertCountEqual(results, [
        self.Path("foo"),
        self.Path("foo", "0"),
        self.Path("foo", "1"),
        self.Path("foo", "bar"),
        self.Path("foo", "baz"),
        self.Path("foo", "bar", "0"),
        self.Path("foo", "baz", "quux"),
        self.Path("foo", "baz", "quux", "0"),
    ])


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
