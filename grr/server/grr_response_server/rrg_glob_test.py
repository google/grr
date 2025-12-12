#!/usr/bin/env python
import pathlib

from absl.testing import absltest

from grr_response_server import rrg_glob


class GlobTest(absltest.TestCase):

  def testLiteral(self):
    glob = rrg_glob.Glob(pathlib.PurePosixPath("/foo/bar/baz"))
    self.assertEqual(glob.root, pathlib.PurePosixPath("/foo/bar/baz"))
    self.assertEqual(glob.root_level, 0)

    self.assertEqual(glob.regex.pattern, "^/foo/bar/baz$")
    self.assertEqual(glob.pruning_regex.pattern, "^/(foo(/bar(/baz)?)?)?$")

    self.assertNotRegex("/", glob.regex)
    self.assertNotRegex("/foo", glob.regex)
    self.assertNotRegex("/foo/bar", glob.regex)
    self.assertRegex("/foo/bar/baz", glob.regex)

    self.assertRegex("/", glob.pruning_regex)
    self.assertRegex("/foo", glob.pruning_regex)
    self.assertRegex("/foo/bar", glob.pruning_regex)
    self.assertRegex("/foo/bar/baz", glob.pruning_regex)

  def testLiteral_Windows(self):
    glob = rrg_glob.Glob(pathlib.PureWindowsPath("C:\\Foo\\Bar"))
    self.assertEqual(glob.root, pathlib.PureWindowsPath("C:\\Foo\\Bar"))
    self.assertEqual(glob.root_level, 0)

    self.assertEqual(glob.regex.pattern, "(?i)^C:\\\\Foo\\\\Bar$")
    self.assertEqual(glob.pruning_regex.pattern, "(?i)^C:\\\\(Foo(\\\\Bar)?)?$")

    self.assertNotRegex("C:\\", glob.regex)
    self.assertNotRegex("C:\\Foo", glob.regex)
    self.assertRegex("C:\\Foo\\Bar", glob.regex)

    self.assertRegex("C:\\", glob.pruning_regex)
    self.assertRegex("C:\\Foo", glob.pruning_regex)
    self.assertRegex("C:\\Foo\\Bar", glob.pruning_regex)

  def testOnlyRoot(self):
    glob = rrg_glob.Glob(pathlib.PurePosixPath("/"))
    self.assertEqual(glob.root, pathlib.PurePosixPath("/"))
    self.assertEqual(glob.root_level, 0)

    self.assertEqual(glob.regex.pattern, "^/$")
    self.assertEqual(glob.pruning_regex.pattern, "^/()?$")

    self.assertRegex("/", glob.regex.pattern)
    self.assertRegex("/", glob.pruning_regex.pattern)

  def testOnlyDrive(self):
    glob = rrg_glob.Glob(pathlib.PureWindowsPath("C:\\"))
    self.assertEqual(glob.root, pathlib.PureWindowsPath("C:\\"))
    self.assertEqual(glob.root_level, 0)

    self.assertEqual(glob.regex.pattern, "(?i)^C:\\\\$")
    self.assertEqual(glob.pruning_regex.pattern, "(?i)^C:\\\\()?$")

    self.assertRegex("C:\\", glob.regex)
    self.assertRegex("C:\\", glob.pruning_regex)

  def testSimpleStar(self):
    glob = rrg_glob.Glob(pathlib.PurePosixPath("/*"))
    self.assertEqual(glob.root, pathlib.PurePosixPath("/"))
    self.assertEqual(glob.root_level, 1)

    regex = glob.regex
    self.assertEqual(regex.pattern, r"^/[^/]*$")

    self.assertRegex("/", regex)
    self.assertRegex("/foo", regex)
    self.assertRegex("/bar", regex)
    self.assertNotRegex("/foo/bar", regex)

    pruning_regex = glob.pruning_regex
    self.assertEqual(pruning_regex.pattern, r"^/([^/]*)?$")

    self.assertRegex("/", pruning_regex)
    self.assertRegex("/foo", pruning_regex)
    self.assertRegex("/bar", pruning_regex)
    self.assertNotRegex("/foo/bar", pruning_regex)

  def testSimpleStar_Windows(self):
    glob = rrg_glob.Glob(pathlib.PureWindowsPath(r"C:\Users\*\NTUSER.DAT"))
    self.assertEqual(glob.root, pathlib.PureWindowsPath(r"C:\Users"))
    self.assertEqual(glob.root_level, 2)

    regex = glob.regex
    self.assertEqual(regex.pattern, r"(?i)^C:\\Users\\[^\\]*\\NTUSER\.DAT$")

    self.assertNotRegex("C:\\", regex)
    self.assertNotRegex("C:\\Users", regex)
    self.assertNotRegex("C:\\Users\\Foo", regex)
    self.assertRegex("C:\\Users\\Foo\\NTUSER.DAT", regex)
    self.assertNotRegex("C:\\Windows", regex)
    self.assertNotRegex("C:\\Users\\Foo\\DOSUSER.DAT", regex)

    pruning_regex = glob.pruning_regex
    self.assertEqual(
        pruning_regex.pattern,
        r"(?i)^C:\\(Users(\\[^\\]*(\\NTUSER\.DAT)?)?)?$",
    )

    self.assertRegex("C:\\", pruning_regex)
    self.assertRegex("C:\\Users", pruning_regex)
    self.assertRegex("C:\\Users\\Foo", pruning_regex)
    self.assertRegex("C:\\Users\\Foo\\NTUSER.DAT", pruning_regex)
    self.assertNotRegex("C:\\Windows", pruning_regex)
    self.assertNotRegex("C:\\Users\\Foo\\DOSUSER.DAT", pruning_regex)

  def testSimpleStar_WeirdCharPaths(self):
    glob = rrg_glob.Glob(pathlib.PurePosixPath("/foo/*"))
    self.assertEqual(glob.root, pathlib.PurePosixPath("/foo"))
    self.assertEqual(glob.root_level, 1)

    regex = glob.regex
    self.assertEqual(regex.pattern, r"^/foo/[^/]*$")

    self.assertRegex("/foo/bar", regex)
    self.assertRegex("/foo/ba?", regex)
    self.assertRegex("/foo/ba*", regex)
    self.assertRegex("/foo/???", regex)
    self.assertRegex("/foo/***", regex)

    pruning_regex = glob.pruning_regex
    self.assertEqual(pruning_regex.pattern, r"^/(foo(/[^/]*)?)?$")

    self.assertRegex("/foo/bar", pruning_regex)
    self.assertRegex("/foo/ba?", pruning_regex)
    self.assertRegex("/foo/ba*", pruning_regex)
    self.assertRegex("/foo/???", pruning_regex)
    self.assertRegex("/foo/***", pruning_regex)

  def testPartialStar(self):
    glob = rrg_glob.Glob(pathlib.PurePosixPath("/foo/ba*"))
    self.assertEqual(glob.root, pathlib.PurePosixPath("/foo"))
    self.assertEqual(glob.root_level, 1)

    regex = glob.regex
    self.assertEqual(regex.pattern, r"^/foo/ba[^/]*$")

    self.assertNotRegex("/", regex)
    self.assertNotRegex("/foo", regex)
    self.assertRegex("/foo/bar", regex)
    self.assertRegex("/foo/baz", regex)
    self.assertRegex("/foo/baaar", regex)
    self.assertRegex("/foo/baaaz", regex)
    self.assertNotRegex("/foo/norf", regex)
    self.assertNotRegex("/foo/bar/baz", regex)

    pruning_regex = glob.pruning_regex
    self.assertEqual(pruning_regex.pattern, r"^/(foo(/ba[^/]*)?)?$")

    self.assertRegex("/", pruning_regex)
    self.assertRegex("/foo", pruning_regex)
    self.assertRegex("/foo/bar", pruning_regex)
    self.assertRegex("/foo/baz", pruning_regex)
    self.assertRegex("/foo/baaar", pruning_regex)
    self.assertRegex("/foo/baaaz", pruning_regex)
    self.assertNotRegex("/foo/norf", pruning_regex)
    self.assertNotRegex("/foo/bar/baz", pruning_regex)

  def testEroteme(self):
    glob = rrg_glob.Glob(pathlib.PurePosixPath("/ba?"))
    self.assertEqual(glob.root, pathlib.PurePosixPath("/"))
    self.assertEqual(glob.root_level, 1)

    regex = glob.regex
    self.assertEqual(regex.pattern, r"^/ba[^/]$")

    self.assertNotRegex("/", regex)
    self.assertRegex("/bar", regex)
    self.assertRegex("/baz", regex)
    self.assertNotRegex("/foo", regex)
    self.assertNotRegex("/ba/", regex)

    pruning_regex = glob.pruning_regex
    self.assertEqual(pruning_regex.pattern, r"^/(ba[^/])?$")

    self.assertRegex("/", pruning_regex)
    self.assertRegex("/bar", pruning_regex)
    self.assertRegex("/baz", pruning_regex)
    self.assertNotRegex("/foo", pruning_regex)
    self.assertNotRegex("/ba/", pruning_regex)

  def testEroteme_WeirdCharPaths(self):
    glob = rrg_glob.Glob(pathlib.PurePosixPath("/foo/???"))
    self.assertEqual(glob.root, pathlib.PurePosixPath("/foo"))
    self.assertEqual(glob.root_level, 1)

    regex = glob.regex
    self.assertEqual(regex.pattern, r"^/foo/[^/][^/][^/]$")

    self.assertRegex("/foo/bar", regex)
    self.assertRegex("/foo/ba?", regex)
    self.assertRegex("/foo/ba*", regex)
    self.assertRegex("/foo/???", regex)
    self.assertRegex("/foo/***", regex)
    self.assertNotRegex("/foo/quux", regex)
    self.assertNotRegex("/foo/fó", regex)

    pruning_regex = glob.pruning_regex
    self.assertEqual(pruning_regex.pattern, r"^/(foo(/[^/][^/][^/])?)?$")

    self.assertRegex("/foo/bar", pruning_regex)
    self.assertRegex("/foo/ba?", pruning_regex)
    self.assertRegex("/foo/ba*", pruning_regex)
    self.assertRegex("/foo/???", pruning_regex)
    self.assertRegex("/foo/***", pruning_regex)
    self.assertNotRegex("/foo/quux", pruning_regex)
    self.assertNotRegex("/foo/fó", pruning_regex)

  def testSet(self):
    glob = rrg_glob.Glob(pathlib.PurePosixPath("/foo/ba[rz]"))
    self.assertEqual(glob.root, pathlib.PurePosixPath("/foo"))
    self.assertEqual(glob.root_level, 1)

    regex = glob.regex
    self.assertEqual(regex.pattern, r"^/foo/ba[rz]$")

    self.assertRegex("/foo/bar", regex)
    self.assertRegex("/foo/baz", regex)
    self.assertNotRegex("/foo/bax", regex)

    pruning_regex = glob.pruning_regex
    self.assertEqual(pruning_regex.pattern, r"^/(foo(/ba[rz])?)?$")

    self.assertRegex("/", pruning_regex)
    self.assertRegex("/foo", pruning_regex)
    self.assertRegex("/foo/bar", pruning_regex)
    self.assertRegex("/foo/baz", pruning_regex)
    self.assertNotRegex("/foo/bax", pruning_regex)

  def testRange_Letters(self):
    glob = rrg_glob.Glob(pathlib.PurePosixPath("/foo/ba[a-z]"))
    self.assertEqual(glob.root, pathlib.PurePosixPath("/foo"))
    self.assertEqual(glob.root_level, 1)

    regex = glob.regex
    self.assertEqual(regex.pattern, r"^/foo/ba[a-z]$")

    self.assertRegex("/foo/bar", regex)
    self.assertRegex("/foo/baz", regex)
    self.assertRegex("/foo/bax", regex)
    self.assertNotRegex("/foo/ba0", regex)

    pruning_regex = glob.pruning_regex
    self.assertEqual(pruning_regex.pattern, r"^/(foo(/ba[a-z])?)?$")

    self.assertRegex("/", pruning_regex)
    self.assertRegex("/foo", pruning_regex)
    self.assertRegex("/foo/bar", pruning_regex)
    self.assertRegex("/foo/baz", pruning_regex)
    self.assertRegex("/foo/bax", pruning_regex)
    self.assertNotRegex("/foo/ba0", pruning_regex)

  def testRange_Digits(self):
    glob = rrg_glob.Glob(pathlib.PurePosixPath("/foo/[0-9]"))
    self.assertEqual(glob.root, pathlib.PurePosixPath("/foo"))
    self.assertEqual(glob.root_level, 1)

    regex = glob.regex
    self.assertEqual(regex.pattern, r"^/foo/[0-9]$")

    self.assertRegex("/foo/0", regex)
    self.assertRegex("/foo/5", regex)
    self.assertRegex("/foo/9", regex)
    self.assertNotRegex("/foo/x", regex)
    self.assertNotRegex("/foo/42", regex)

    pruning_regex = glob.pruning_regex
    self.assertEqual(pruning_regex.pattern, r"^/(foo(/[0-9])?)?$")

    self.assertRegex("/", pruning_regex)
    self.assertRegex("/foo", pruning_regex)
    self.assertRegex("/foo/0", pruning_regex)
    self.assertRegex("/foo/5", pruning_regex)
    self.assertRegex("/foo/9", pruning_regex)
    self.assertNotRegex("/foo/x", pruning_regex)
    self.assertNotRegex("/foo/42", pruning_regex)

  def testLiteralSuffix(self):
    glob = rrg_glob.Glob(pathlib.PurePosixPath("/*/foo"))
    self.assertEqual(glob.root, pathlib.PurePosixPath("/"))
    self.assertEqual(glob.root_level, 2)

    regex = glob.regex
    self.assertEqual(regex.pattern, r"^/[^/]*/foo$")

    self.assertNotRegex("/", regex)
    self.assertNotRegex("/bar", regex)
    self.assertNotRegex("/baz", regex)
    self.assertRegex("/bar/foo", regex)
    self.assertRegex("/baz/foo", regex)
    self.assertNotRegex("/bar/fo", regex)
    self.assertNotRegex("/baz/fo", regex)
    self.assertNotRegex("/bar/fooo", regex)
    self.assertNotRegex("/baz/fooo", regex)

    pruning_regex = glob.pruning_regex
    self.assertEqual(pruning_regex.pattern, r"^/([^/]*(/foo)?)?$")

    self.assertRegex("/", pruning_regex)
    self.assertRegex("/bar", pruning_regex)
    self.assertRegex("/baz", pruning_regex)
    self.assertRegex("/bar/foo", pruning_regex)
    self.assertRegex("/baz/foo", pruning_regex)
    self.assertNotRegex("/bar/fo", pruning_regex)
    self.assertNotRegex("/baz/fo", pruning_regex)
    self.assertNotRegex("/bar/fooo", pruning_regex)
    self.assertNotRegex("/baz/fooo", pruning_regex)

  def testLiteralMultiComponentSuffix(self):
    glob = rrg_glob.Glob(pathlib.PurePosixPath("/*/foo/quux"))
    self.assertEqual(glob.root, pathlib.PurePosixPath("/"))
    self.assertEqual(glob.root_level, 3)

    regex = glob.regex
    self.assertEqual(regex.pattern, r"^/[^/]*/foo/quux$")

    self.assertNotRegex("/", regex)
    self.assertNotRegex("/bar", regex)
    self.assertNotRegex("/baz", regex)
    self.assertNotRegex("/bar/foo", regex)
    self.assertNotRegex("/baz/foo", regex)
    self.assertRegex("/bar/foo/quux", regex)
    self.assertRegex("/baz/foo/quux", regex)
    self.assertNotRegex("/bar/fo", regex)
    self.assertNotRegex("/baz/fo", regex)
    self.assertNotRegex("/bar/fooo", regex)
    self.assertNotRegex("/baz/fooo", regex)
    self.assertNotRegex("/bar/foo/qux", regex)
    self.assertNotRegex("/baz/foo/qux", regex)

    pruning_regex = glob.pruning_regex
    self.assertEqual(pruning_regex.pattern, r"^/([^/]*(/foo(/quux)?)?)?$")

    self.assertRegex("/", pruning_regex)
    self.assertRegex("/bar", pruning_regex)
    self.assertRegex("/baz", pruning_regex)
    self.assertRegex("/bar/foo", pruning_regex)
    self.assertRegex("/baz/foo", pruning_regex)
    self.assertRegex("/bar/foo/quux", pruning_regex)
    self.assertRegex("/baz/foo/quux", pruning_regex)
    self.assertNotRegex("/bar/fo", pruning_regex)
    self.assertNotRegex("/baz/fo", pruning_regex)
    self.assertNotRegex("/bar/fooo", pruning_regex)
    self.assertNotRegex("/baz/fooo", pruning_regex)
    self.assertNotRegex("/bar/foo/qux", pruning_regex)
    self.assertNotRegex("/baz/foo/qux", pruning_regex)

  def testTwoStarComponent(self):
    glob = rrg_glob.Glob(pathlib.PurePosixPath("/*foo*"))
    self.assertEqual(glob.root, pathlib.PurePosixPath("/"))
    self.assertEqual(glob.root_level, 1)

    regex = glob.regex
    self.assertEqual(regex.pattern, r"^/[^/]*foo[^/]*$")

    self.assertNotRegex("/", regex)
    self.assertRegex("/foo", regex)
    self.assertRegex("/barfoo", regex)
    self.assertRegex("/foobar", regex)
    self.assertRegex("/barfoobaz", regex)
    self.assertNotRegex("/bar", regex)
    self.assertNotRegex("/foo/bar", regex)

    pruning_regex = glob.pruning_regex
    self.assertEqual(pruning_regex.pattern, r"^/([^/]*foo[^/]*)?$")

    self.assertRegex("/", pruning_regex)
    self.assertRegex("/foo", pruning_regex)
    self.assertRegex("/barfoo", pruning_regex)
    self.assertRegex("/foobar", pruning_regex)
    self.assertRegex("/barfoobaz", pruning_regex)
    self.assertNotRegex("/bar", pruning_regex)
    self.assertNotRegex("/foo/bar", pruning_regex)

  def testMultipleStars(self):
    glob = rrg_glob.Glob(pathlib.PurePosixPath("/*/foo/*"))
    self.assertEqual(glob.root, pathlib.PurePosixPath("/"))
    self.assertEqual(glob.root_level, 3)

    regex = glob.regex
    self.assertEqual(regex.pattern, r"^/[^/]*/foo/[^/]*$")

    self.assertNotRegex("/", regex)
    self.assertNotRegex("/bar", regex)
    self.assertNotRegex("/baz", regex)
    self.assertNotRegex("/bar/foo", regex)
    self.assertNotRegex("/baz/foo", regex)
    self.assertRegex("/bar/foo/baz", regex)
    self.assertRegex("/baz/foo/bar", regex)
    self.assertNotRegex("/bar/quux", regex)
    self.assertNotRegex("/baz/quux", regex)
    self.assertNotRegex("/bar/foo/baz/quux", regex)
    self.assertNotRegex("/baz/foo/bar/quux", regex)

    pruning_regex = glob.pruning_regex
    self.assertEqual(pruning_regex.pattern, r"^/([^/]*(/foo(/[^/]*)?)?)?$")

    self.assertRegex("/", pruning_regex)
    self.assertRegex("/bar", pruning_regex)
    self.assertRegex("/baz", pruning_regex)
    self.assertRegex("/bar/foo", pruning_regex)
    self.assertRegex("/baz/foo", pruning_regex)
    self.assertRegex("/bar/foo/baz", pruning_regex)
    self.assertRegex("/baz/foo/bar", pruning_regex)
    self.assertNotRegex("/bar/quux", pruning_regex)
    self.assertNotRegex("/baz/quux", pruning_regex)
    self.assertNotRegex("/bar/foo/baz/quux", pruning_regex)
    self.assertNotRegex("/baz/foo/bar/quux", pruning_regex)

  def testRecursive_Leaf(self):
    glob = rrg_glob.Glob(pathlib.PurePosixPath("/foo/**4"))
    self.assertEqual(glob.root, pathlib.PurePosixPath("/foo"))
    self.assertEqual(glob.root_level, 4)

    regex = glob.regex
    self.assertEqual(regex.pattern, r"^/foo(/[^/]*){0,4}$")

    self.assertNotRegex("/", regex)
    self.assertRegex("/foo", regex)
    self.assertRegex("/foo/bar", regex)
    self.assertRegex("/foo/bar/baz", regex)
    self.assertRegex("/foo/bar/baz/quux", regex)
    self.assertRegex("/foo/bar/baz/quux/norf", regex)
    self.assertNotRegex("/foo/bar/baz/quux/norf/thud", regex)

    pruning_regex = glob.pruning_regex
    self.assertEqual(pruning_regex.pattern, r"^/(foo((/[^/]*){0,4})?)?$")

    self.assertRegex("/", pruning_regex)
    self.assertRegex("/foo", pruning_regex)
    self.assertRegex("/foo/bar", pruning_regex)
    self.assertRegex("/foo/bar/baz", pruning_regex)
    self.assertRegex("/foo/bar/baz/quux", pruning_regex)
    self.assertRegex("/foo/bar/baz/quux/norf", pruning_regex)
    self.assertNotRegex("/foo/bar/baz/quux/norf/thud", pruning_regex)

  def testRecursive_NonLeaf(self):
    glob = rrg_glob.Glob(pathlib.PurePosixPath("/foo/**2/bar"))
    self.assertEqual(glob.root, pathlib.PurePosixPath("/foo"))
    self.assertEqual(glob.root_level, 3)

    regex = glob.regex
    self.assertEqual(regex.pattern, r"^/foo(/[^/]*){0,2}/bar$")

    self.assertNotRegex("/", regex)
    self.assertNotRegex("/foo", regex)
    self.assertRegex("/foo/bar", regex)
    self.assertNotRegex("/foobar", regex)
    self.assertNotRegex("/foo/quux", regex)
    self.assertRegex("/foo/quux/bar", regex)
    self.assertNotRegex("/foo/quux/norf", regex)
    self.assertRegex("/foo/quux/norf/bar", regex)
    self.assertNotRegex("/foo/quux/norf/baz", regex)
    self.assertNotRegex("/foo/quux/norf/thud/bar", regex)

    pruning_regex = glob.pruning_regex
    self.assertEqual(pruning_regex.pattern, r"^/(foo((/[^/]*){0,2}(/bar)?)?)?$")

    self.assertRegex("/", pruning_regex)
    self.assertRegex("/foo", pruning_regex)
    self.assertRegex("/foo/bar", pruning_regex)
    self.assertNotRegex("/foobar", pruning_regex)
    self.assertRegex("/foo/quux", pruning_regex)
    self.assertRegex("/foo/quux/bar", pruning_regex)
    self.assertRegex("/foo/quux/norf", pruning_regex)
    self.assertRegex("/foo/quux/norf/bar", pruning_regex)
    self.assertNotRegex("/foo/quux/norf/baz", pruning_regex)
    self.assertNotRegex("/foo/quux/norf/thud/bar", pruning_regex)

  def testRecursive_Root(self):
    glob = rrg_glob.Glob(pathlib.PurePosixPath("/**3"))
    self.assertEqual(glob.root, pathlib.PurePosixPath("/"))
    self.assertEqual(glob.root_level, 3)

    regex = glob.regex
    self.assertEqual(regex.pattern, r"^(/[^/]*){0,3}$")

    self.assertRegex("/", regex)
    self.assertRegex("/foo", regex)
    self.assertRegex("/foo/bar", regex)
    self.assertRegex("/foo/bar/baz", regex)
    self.assertNotRegex("/foo/bar/baz/quux", regex)

    pruning_regex = glob.pruning_regex
    self.assertEqual(pruning_regex.pattern, r"^((/[^/]*){0,3})?$")

    self.assertRegex("/", pruning_regex)
    self.assertRegex("/foo", pruning_regex)
    self.assertRegex("/foo/bar", pruning_regex)
    self.assertRegex("/foo/bar/baz", pruning_regex)
    self.assertNotRegex("/foo/bar/baz/quux", pruning_regex)

  def testRecursive_Windows(self):
    glob = rrg_glob.Glob(pathlib.PureWindowsPath(r"C:\**4\*.exe"))
    self.assertEqual(glob.root, pathlib.PureWindowsPath("C:\\"))
    self.assertEqual(glob.root_level, 5)

    regex = glob.regex
    self.assertEqual(regex.pattern, r"(?i)^C:(\\[^\\]*){0,4}\\[^\\]*\.exe$")

    self.assertNotRegex("C:\\", regex)
    self.assertRegex("C:\\blargh.exe", regex)
    self.assertNotRegex("C:\\Foo", regex)
    self.assertRegex("C:\\Foo\\blargh.exe", regex)
    self.assertNotRegex("C:\\Foo\\Bar", regex)
    self.assertRegex("C:\\Foo\\Bar\\blargh.exe", regex)
    self.assertNotRegex("C:\\Foo\\Bar\\Baz", regex)
    self.assertRegex("C:\\Foo\\Bar\\Baz\\blargh.exe", regex)
    self.assertNotRegex("C:\\Foo\\Bar\\Baz\\Quux", regex)
    self.assertRegex("C:\\Foo\\Bar\\Baz\\Quux\\blargh.exe", regex)
    self.assertNotRegex("D:\\blargh.exe", regex)
    self.assertNotRegex("C:\\Foo\\Bar\\Baz\\Quux\\Thud\\blargh.exe", regex)

    pruning_regex = glob.pruning_regex
    self.assertEqual(
        pruning_regex.pattern,
        r"(?i)^C:((\\[^\\]*){0,4}(\\[^\\]*\.exe)?)?$",
    )

    self.assertRegex("C:\\", pruning_regex)
    self.assertRegex("C:\\blargh.exe", pruning_regex)
    self.assertRegex("C:\\Foo", pruning_regex)
    self.assertRegex("C:\\Foo\\blargh.exe", pruning_regex)
    self.assertRegex("C:\\Foo\\Bar", pruning_regex)
    self.assertRegex("C:\\Foo\\Bar\\blargh.exe", pruning_regex)
    self.assertRegex("C:\\Foo\\Bar\\Baz", pruning_regex)
    self.assertRegex("C:\\Foo\\Bar\\Baz\\blargh.exe", pruning_regex)
    self.assertRegex("C:\\Foo\\Bar\\Baz\\Quux", pruning_regex)
    self.assertRegex("C:\\Foo\\Bar\\Baz\\Quux\\blargh.exe", pruning_regex)
    self.assertNotRegex("D:\\blargh.exe", pruning_regex)
    self.assertNotRegex(
        "C:\\Foo\\Bar\\Baz\\Quux\\Thud\\blargh.exe",
        pruning_regex,
    )

  def testCase_Posix(self):
    glob = rrg_glob.Glob(pathlib.PurePosixPath("/FOO/bar"))

    self.assertRegex("/FOO/bar", glob.regex)
    self.assertNotRegex("/foo/bar", glob.regex)
    self.assertNotRegex("/FOO/BAR", glob.regex)

    self.assertRegex("/FOO/bar", glob.pruning_regex)
    self.assertNotRegex("/foo/bar", glob.pruning_regex)
    self.assertNotRegex("/FOO/BAR", glob.pruning_regex)

  def testCase_Windows(self):
    glob = rrg_glob.Glob(pathlib.PureWindowsPath("C:\\FOO\\bar"))

    self.assertRegex("C:\\FOO\\bar", glob.regex)
    self.assertRegex("C:\\foo\\bar", glob.regex)
    self.assertRegex("C:\\FOO\\BAR", glob.regex)

    self.assertRegex("C:\\FOO\\bar", glob.pruning_regex)
    self.assertRegex("C:\\foo\\bar", glob.pruning_regex)
    self.assertRegex("C:\\FOO\\BAR", glob.pruning_regex)


if __name__ == "__main__":
  absltest.main()
