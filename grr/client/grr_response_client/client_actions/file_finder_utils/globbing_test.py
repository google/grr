#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division

from __future__ import unicode_literals

import contextlib
import io
import os
import platform
import unittest

from absl import app
from absl.testing import absltest
from future.builtins import zip
from typing import Iterator
from typing import Sequence
from typing import Text

from grr_response_client.client_actions.file_finder_utils import globbing
from grr_response_client.vfs_handlers import files
from grr_response_core.lib.util import temp
from grr.test_lib import test_lib


class RecursiveComponentTest(absltest.TestCase):

  def testSimple(self):
    filepaths = [
        ("foo", "0"),
        ("foo", "1"),
        ("foo", "bar", "0"),
        ("baz", "0"),
        ("baz", "1"),
    ]

    component = globbing.RecursiveComponent()

    with DirHierarchy(filepaths) as hierarchy:
      results = list(component.Generate(hierarchy(())))
      self.assertCountEqual(results, [
          hierarchy(("foo",)),
          hierarchy(("foo", "0")),
          hierarchy(("foo", "1")),
          hierarchy(("foo", "bar")),
          hierarchy(("foo", "bar", "0")),
          hierarchy(("baz",)),
          hierarchy(("baz", "0")),
          hierarchy(("baz", "1")),
      ])

      results = list(component.Generate(hierarchy(("foo",))))
      self.assertCountEqual(results, [
          hierarchy(("foo", "0")),
          hierarchy(("foo", "1")),
          hierarchy(("foo", "bar")),
          hierarchy(("foo", "bar", "0")),
      ])

      results = list(component.Generate(hierarchy(("baz",))))
      self.assertCountEqual(results, [
          hierarchy(("baz", "0")),
          hierarchy(("baz", "1")),
      ])

      results = list(component.Generate(hierarchy(("foo", "bar"))))
      self.assertCountEqual(results, [
          hierarchy(("foo", "bar", "0")),
      ])

  def testMaxDepth(self):
    filepaths = [
        ("foo", "0"),
        ("foo", "1"),
        ("foo", "bar", "0"),
        ("foo", "bar", "baz", "0"),
    ]

    component = globbing.RecursiveComponent(max_depth=3)

    with DirHierarchy(filepaths) as hierarchy:
      results = list(component.Generate(hierarchy(())))

      # Files at level lesser than 3 should be included.
      self.assertIn(hierarchy(("foo",)), results)
      self.assertIn(hierarchy(("foo", "0")), results)
      self.assertIn(hierarchy(("foo", "1")), results)
      self.assertIn(hierarchy(("foo", "bar")), results)

      # Files at level equal to 3 should be included.
      self.assertIn(hierarchy(("foo", "bar", "0")), results)
      self.assertIn(hierarchy(("foo", "bar", "baz")), results)

      # Files at level bigger that 3 should not be included.
      self.assertNotIn(hierarchy(("foo", "bar", "baz", "0")), results)

  @unittest.skipIf(
      platform.system() == "Windows",
      reason="Symlinks are not available on Windows")
  def testFollowLinks(self):
    filepaths = [
        ("foo", "0"),
        ("foo", "bar", "0"),
        ("foo", "baz", "0"),
        ("foo", "baz", "1"),
        ("quux", "0"),
        ("norf", "0"),
    ]

    with DirHierarchy(filepaths) as hierarchy:
      os.symlink(hierarchy(("foo", "bar")), hierarchy(("quux", "bar")))
      os.symlink(hierarchy(("foo", "baz")), hierarchy(("quux", "baz")))
      os.symlink(hierarchy(("quux",)), hierarchy(("norf", "quux")))

      opts = globbing.PathOpts(follow_links=True)
      component = globbing.RecursiveComponent(opts=opts)

      # It should resolve two links and recur to linked directories.
      results = list(component.Generate(hierarchy(("quux",))))
      self.assertCountEqual(results, [
          hierarchy(("quux", "0")),
          hierarchy(("quux", "bar")),
          hierarchy(("quux", "bar", "0")),
          hierarchy(("quux", "baz")),
          hierarchy(("quux", "baz", "0")),
          hierarchy(("quux", "baz", "1")),
      ])

      # It should resolve symlinks recursively.
      results = list(component.Generate(hierarchy(("norf",))))
      self.assertCountEqual(results, [
          hierarchy(("norf", "0")),
          hierarchy(("norf", "quux")),
          hierarchy(("norf", "quux", "0")),
          hierarchy(("norf", "quux", "bar")),
          hierarchy(("norf", "quux", "bar", "0")),
          hierarchy(("norf", "quux", "baz")),
          hierarchy(("norf", "quux", "baz", "0")),
          hierarchy(("norf", "quux", "baz", "1")),
      ])

      opts = globbing.PathOpts(follow_links=False)
      component = globbing.RecursiveComponent(opts=opts)

      # It should list symlinks but should not recur to linked directories.
      results = list(component.Generate(hierarchy(())))
      self.assertCountEqual(results, [
          hierarchy(("foo",)),
          hierarchy(("foo", "0")),
          hierarchy(("foo", "bar")),
          hierarchy(("foo", "bar", "0")),
          hierarchy(("foo", "baz")),
          hierarchy(("foo", "baz", "0")),
          hierarchy(("foo", "baz", "1")),
          hierarchy(("quux",)),
          hierarchy(("quux", "0")),
          hierarchy(("quux", "bar")),
          hierarchy(("quux", "baz")),
          hierarchy(("norf",)),
          hierarchy(("norf", "0")),
          hierarchy(("norf", "quux")),
      ])

  def testInvalidDirpath(self):
    component = globbing.RecursiveComponent()

    results = list(component.Generate("/foo/bar/baz"))
    self.assertCountEqual(results, [])


class GlobComponentTest(absltest.TestCase):

  def testLiterals(self):
    filepaths = [
        ("foo",),
        ("bar",),
        ("baz",),
    ]

    with DirHierarchy(filepaths) as hierarchy:
      component = globbing.GlobComponent("foo")

      results = list(component.Generate(hierarchy(())))
      self.assertCountEqual(results, [
          hierarchy(("foo",)),
      ])

      component = globbing.GlobComponent("bar")

      results = list(component.Generate(hierarchy(())))
      self.assertCountEqual(results, [
          hierarchy(("bar",)),
      ])

  def testStar(self):
    filepaths = [
        ("foo",),
        ("bar",),
        ("baz",),
        ("quux",),
    ]

    with DirHierarchy(filepaths) as hierarchy:
      component = globbing.GlobComponent("*")

      results = list(component.Generate(hierarchy(())))
      self.assertCountEqual(results, [
          hierarchy(("foo",)),
          hierarchy(("bar",)),
          hierarchy(("baz",)),
          hierarchy(("quux",)),
      ])

      component = globbing.GlobComponent("ba*")

      results = list(component.Generate(hierarchy(())))
      self.assertCountEqual(results, [
          hierarchy(("bar",)),
          hierarchy(("baz",)),
      ])

  def testQuestionmark(self):
    filepaths = [
        ("foo",),
        ("bar",),
        ("baz",),
        ("barg",),
    ]

    component = globbing.GlobComponent("ba?")

    with DirHierarchy(filepaths) as hierarchy:
      results = list(component.Generate(hierarchy(())))
      self.assertCountEqual(results, [
          hierarchy(("bar",)),
          hierarchy(("baz",)),
      ])

  def testSimpleClass(self):
    filepaths = [
        ("foo",),
        ("bar",),
        ("baz",),
        ("baf",),
    ]

    component = globbing.GlobComponent("ba[rz]")

    with DirHierarchy(filepaths) as hierarchy:
      results = list(component.Generate(hierarchy(())))
      self.assertCountEqual(results, [
          hierarchy(("baz",)),
          hierarchy(("bar",)),
      ])

  def testRangeClass(self):
    filepaths = [
        ("foo",),
        ("8AR",),
        ("bar",),
        ("4815162342",),
        ("quux42",),
    ]

    with DirHierarchy(filepaths) as hierarchy:
      component = globbing.GlobComponent("[a-z]*")

      results = list(component.Generate(hierarchy(())))
      self.assertCountEqual(results, [
          hierarchy(("foo",)),
          hierarchy(("bar",)),
          hierarchy(("quux42",)),
      ])

      component = globbing.GlobComponent("[0-9]*")

      results = list(component.Generate(hierarchy(())))
      self.assertCountEqual(results, [
          hierarchy(("8AR",)),
          hierarchy(("4815162342",)),
      ])

      component = globbing.GlobComponent("*[0-9]")

      results = list(component.Generate(hierarchy(())))
      self.assertCountEqual(results, [
          hierarchy(("4815162342",)),
          hierarchy(("quux42",)),
      ])

  def testMultiRangeClass(self):
    filepaths = [
        ("f00",),
        ("b4R",),
        ("8az",),
        ("quux",),
    ]

    component = globbing.GlobComponent("[a-z][a-z0-9]*")

    with DirHierarchy(filepaths) as hierarchy:
      results = list(component.Generate(hierarchy(())))
      self.assertCountEqual(results, [
          hierarchy(("f00",)),
          hierarchy(("b4R",)),
          hierarchy(("quux",)),
      ])

  def testComplementationClass(self):
    filepaths = [
        ("foo",),
        ("bar",),
        ("123",),
    ]

    with DirHierarchy(filepaths) as hierarchy:
      component = globbing.GlobComponent("*[!0-9]*")

      results = list(component.Generate(hierarchy(())))
      self.assertCountEqual(results, [
          hierarchy(("foo",)),
          hierarchy(("bar",)),
      ])

  # TODO(hanuszczak): This test should be split into multiple cases.
  def testCornerCases(self):
    filepaths = [
        ("[",),
        ("-",),
        ("]",),
        ("!",),
        ("foo",),
    ]

    # `*` and `?` are disallowed in names of files on Windows.
    if platform.system() != "Windows":
      filepaths.append("*")
      filepaths.append("?")

    with DirHierarchy(filepaths) as hierarchy:
      component = globbing.GlobComponent("[][-]")

      results = list(component.Generate(hierarchy(())))
      self.assertCountEqual(results, [
          hierarchy(("[",)),
          hierarchy(("-",)),
          hierarchy(("]",)),
      ])

      component = globbing.GlobComponent("[!]f-]*")

      results = list(component.Generate(hierarchy(())))
      self.assertIn(hierarchy(("[",)), results)
      self.assertIn(hierarchy(("!",)), results)

      if platform.system() != "Windows":
        self.assertIn(hierarchy(("*",)), results)
        self.assertIn(hierarchy(("?",)), results)

      if platform.system() != "Windows":
        component = globbing.GlobComponent("[*?]")

        results = list(component.Generate(hierarchy(())))
        self.assertCountEqual(results, [
            hierarchy(("*",)),
            hierarchy(("?",)),
        ])

  @unittest.skipIf(
      platform.system() == "Windows",
      reason="Windows disallows usage of whitespace-only paths")
  def testWhitespace(self):
    filepaths = [
        ("foo bar",),
        ("   ",),
        ("quux",),
    ]

    component = globbing.GlobComponent("* *")

    with DirHierarchy(filepaths) as hierarchy:
      results = list(component.Generate(hierarchy(())))
      self.assertCountEqual(results, [
          hierarchy(("foo bar",)),
          hierarchy(("   ",)),
      ])

  def testCaseInsensivity(self):
    filepaths = [
        ("foo",),
        ("BAR",),
        ("BaZ",),
        ("qUuX",),
    ]

    with DirHierarchy(filepaths) as hierarchy:
      component = globbing.GlobComponent("b*")
      results = list(component.Generate(hierarchy(())))
      self.assertCountEqual(results, [
          hierarchy(("BAR",)),
          hierarchy(("BaZ",)),
      ])

      component = globbing.GlobComponent("quux")
      results = list(component.Generate(hierarchy(())))
      self.assertCountEqual(results, [
          hierarchy(("qUuX",)),
      ])

      component = globbing.GlobComponent("FoO")
      results = list(component.Generate(hierarchy(())))
      self.assertCountEqual(results, [
          hierarchy(("foo",)),
      ])

  def testUnicodeGlobbing(self):
    filepaths = [
        ("ścieżka",),
        ("dróżka",),
    ]

    with DirHierarchy(filepaths) as hierarchy:
      results = list(globbing.GlobComponent("ścieżka").Generate(hierarchy(())))
      self.assertCountEqual(results, [
          hierarchy(("ścieżka",)),
      ])

      results = list(globbing.GlobComponent("dróżka").Generate(hierarchy(())))
      self.assertCountEqual(results, [
          hierarchy(("dróżka",)),
      ])

      results = list(globbing.GlobComponent("*żka").Generate(hierarchy(())))
      self.assertCountEqual(results, [
          hierarchy(("ścieżka",)),
          hierarchy(("dróżka",)),
      ])

  def testUnicodeSubfolderGlobbing(self):
    filepaths = [
        ("zbiór", "podścieżka"),
        ("zbiór", "poddróżka"),
    ]

    component = globbing.GlobComponent("*")

    with DirHierarchy(filepaths) as hierarchy:
      results = list(component.Generate(hierarchy(("zbiór",))))
      self.assertCountEqual(results, [
          hierarchy(("zbiór", "podścieżka")),
          hierarchy(("zbiór", "poddróżka")),
      ])


class CurrentComponentTest(absltest.TestCase):

  def testSimple(self):
    filepaths = [
        ("foo", "bar", "0"),
        ("foo", "baz", "0"),
    ]

    component = globbing.CurrentComponent()

    with DirHierarchy(filepaths) as hierarchy:
      results = list(component.Generate(hierarchy(("foo",))))
      self.assertCountEqual(results, [hierarchy(("foo",))])

      results = list(component.Generate(hierarchy(("foo", "bar"))))
      self.assertCountEqual(results, [hierarchy(("foo", "bar"))])

      results = list(component.Generate(hierarchy(("foo", "baz"))))
      self.assertCountEqual(results, [hierarchy(("foo", "baz"))])


class ParentComponentTest(absltest.TestCase):

  def testSimple(self):
    filepaths = [
        ("foo", "0"),
        ("foo", "bar", "0"),
        ("foo", "bar", "baz", "0"),
    ]

    component = globbing.ParentComponent()

    with DirHierarchy(filepaths) as hierarchy:
      results = list(component.Generate(hierarchy(("foo",))))
      self.assertCountEqual(results, [hierarchy(())])

      results = list(component.Generate(hierarchy(("foo", "bar"))))
      self.assertCountEqual(results, [hierarchy(("foo",))])

      results = list(component.Generate(hierarchy(("foo", "bar", "baz"))))
      self.assertCountEqual(results, [hierarchy(("foo", "bar"))])


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


class ExpandGlobsTest(absltest.TestCase):

  def testWildcards(self):
    filepaths = [
        ("foo", "bar", "0"),
        ("foo", "baz", "1"),
        ("foo", "norf", "0"),
        ("quux", "bar", "0"),
        ("quux", "baz", "0"),
        ("quux", "norf", "0"),
    ]

    with DirHierarchy(filepaths) as hierarchy:
      path = hierarchy(("*", "ba?", "0"))

      results = list(globbing.ExpandGlobs(path))
      self.assertCountEqual(results, [
          hierarchy(("foo", "bar", "0")),
          hierarchy(("quux", "bar", "0")),
          hierarchy(("quux", "baz", "0")),
      ])

  def testRecursion(self):
    filepaths = [
        ("foo", "bar", "baz", "0"),
        ("foo", "bar", "0"),
        ("foo", "quux", "0"),
        ("foo", "quux", "1"),
    ]

    with DirHierarchy(filepaths) as hierarchy:
      path = hierarchy(("foo", "**", "0"))

      results = list(globbing.ExpandGlobs(path))
      self.assertCountEqual(results, [
          hierarchy(("foo", "bar", "baz", "0")),
          hierarchy(("foo", "bar", "0")),
          hierarchy(("foo", "quux", "0")),
      ])

  def testMixed(self):
    filepaths = [
        ("foo", "bar", "0"),
        ("norf", "bar", "0"),
        ("norf", "baz", "0"),
        ("norf", "baz", "1"),
        ("norf", "baz", "7"),
        ("quux", "bar", "0"),
        ("quux", "baz", "1"),
        ("quux", "baz", "2"),
    ]

    with DirHierarchy(filepaths) as hierarchy:
      path = hierarchy(("**", "ba?", "[0-2]"))

      results = list(globbing.ExpandGlobs(path))
      self.assertCountEqual(results, [
          hierarchy(("foo", "bar", "0")),
          hierarchy(("norf", "bar", "0")),
          hierarchy(("norf", "baz", "0")),
          hierarchy(("norf", "baz", "1")),
          hierarchy(("quux", "bar", "0")),
          hierarchy(("quux", "baz", "1")),
          hierarchy(("quux", "baz", "2")),
      ])

  def testEmpty(self):
    with self.assertRaises(ValueError):
      list(globbing.ExpandGlobs(""))

  def testRelative(self):
    with self.assertRaises(ValueError):
      list(globbing.ExpandGlobs(os.path.join("foo", "bar")))

  def testCurrent(self):
    filepaths = [
        ("foo", "bar", "0"),
        ("foo", "bar", "1"),
        ("quux", "bar", "0"),
    ]

    with DirHierarchy(filepaths) as hierarchy:
      path = hierarchy(("foo", os.path.curdir, "bar", "*"))

      results = list(globbing.ExpandGlobs(path))
      self.assertCountEqual(results, [
          hierarchy(("foo", "bar", "0")),
          hierarchy(("foo", "bar", "1")),
      ])

      path = hierarchy((os.path.curdir, "*", "bar", "0"))

      results = list(globbing.ExpandGlobs(path))
      self.assertCountEqual(results, [
          hierarchy(("foo", "bar", "0")),
          hierarchy(("quux", "bar", "0")),
      ])

  def testParent(self):
    filepaths = [
        ("foo", "0"),
        ("foo", "1"),
        ("foo", "bar", "0"),
        ("bar", "0"),
    ]

    with DirHierarchy(filepaths) as hierarchy:
      path = hierarchy(("foo", "*"))

      results = list(globbing.ExpandGlobs(path))
      self.assertCountEqual(results, [
          hierarchy(("foo", "0")),
          hierarchy(("foo", "1")),
          hierarchy(("foo", "bar")),
      ])

      path = hierarchy(("foo", os.path.pardir, "*"))

      results = list(globbing.ExpandGlobs(path))
      self.assertCountEqual(results, [
          hierarchy(("foo",)),
          hierarchy(("bar",)),
      ])


class ExpandPathTest(absltest.TestCase):

  def testGlobAndGroup(self):
    filepaths = [
        ("foo", "bar", "0"),
        ("foo", "bar", "1"),
        ("foo", "baz", "0"),
        ("foo", "baz", "1"),
        ("foo", "quux", "0"),
        ("foo", "quux", "1"),
    ]

    with DirHierarchy(filepaths) as hierarchy:
      path = hierarchy(("foo", "ba{r,z}", "*"))
      results = list(globbing.ExpandPath(path))
      self.assertCountEqual(results, [
          hierarchy(("foo", "bar", "0")),
          hierarchy(("foo", "bar", "1")),
          hierarchy(("foo", "baz", "0")),
          hierarchy(("foo", "baz", "1")),
      ])

      path = hierarchy(("foo", "ba*", "{0,1}"))
      results = list(globbing.ExpandPath(path))
      self.assertCountEqual(results, [
          hierarchy(("foo", "bar", "0")),
          hierarchy(("foo", "bar", "1")),
          hierarchy(("foo", "baz", "0")),
          hierarchy(("foo", "baz", "1")),
      ])

  def testRecursiveAndGroup(self):
    filepaths = [
        ("foo", "0"),
        ("foo", "1"),
        ("foo", "bar", "0"),
        ("foo", "baz", "quux", "0"),
    ]

    with DirHierarchy(filepaths) as hierarchy:
      path = hierarchy(("foo", "**"))
      results = list(globbing.ExpandPath(path))
      self.assertCountEqual(results, [
          hierarchy(("foo", "0")),
          hierarchy(("foo", "1")),
          hierarchy(("foo", "bar")),
          hierarchy(("foo", "baz")),
          hierarchy(("foo", "bar", "0")),
          hierarchy(("foo", "baz", "quux")),
          hierarchy(("foo", "baz", "quux", "0")),
      ])

      path = hierarchy(("foo", "{.,**}"))
      results = list(globbing.ExpandPath(path))
      self.assertCountEqual(results, [
          hierarchy(("foo",)),
          hierarchy(("foo", "0")),
          hierarchy(("foo", "1")),
          hierarchy(("foo", "bar")),
          hierarchy(("foo", "baz")),
          hierarchy(("foo", "bar", "0")),
          hierarchy(("foo", "baz", "quux")),
          hierarchy(("foo", "baz", "quux", "0")),
      ])


class DirHierarchyContext(object):
  """A context within which the file hierarchy exists."""

  def __init__(self, dirpath):
    """Initializes the hierarchy context.

    Args:
      dirpath: A root directory of the hierarchy.
    """
    if platform.system() == "Windows":
      # On Windows, the given path can sometimes have incorrect drive case. So,
      # because the file-finder is case-correcting this and we just use want to
      # use plain equality for comparing paths, we do the same here.
      drive, tail = os.path.splitdrive(dirpath)
      dirpath = drive.upper() + tail

    self._dirpath = dirpath

  def __call__(self, components):
    """Constructs an absolute path to the specified file of the hierarchy.

    Args:
      components: A components of the relative path.

    Returns:
      An absolute path corresponding to the given relative path.
    """
    return os.path.join(self._dirpath, *components)


@contextlib.contextmanager
def DirHierarchy(
    filepaths):
  """A context manager that setups a fake directory hierarchy.

  Args:
    filepaths: A list of paths that should exist in the hierarchy.

  Yields:
    A context within which the fake hierarchy exists.
  """
  with temp.AutoTempDirPath(remove_non_empty=True) as temp_dirpath:
    hierarchy = DirHierarchyContext(temp_dirpath)

    for filepath in map(hierarchy, filepaths):
      dirpath = os.path.dirname(filepath)

      try:
        if not os.path.exists(dirpath):
          os.makedirs(dirpath)
        with io.open(filepath, "a"):
          pass
      except UnicodeEncodeError:
        raise unittest.SkipTest("Unicode not supported by the filesystem")

    try:
      yield hierarchy
    finally:
      # TODO: Required to clean-up the temp directory.
      files.FlushHandleCache()


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
