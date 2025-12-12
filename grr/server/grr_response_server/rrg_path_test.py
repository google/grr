#!/usr/bin/env python
import pathlib

from absl.testing import absltest

from grr_response_server import rrg_path
from grr_response_proto.rrg import fs_pb2 as rrg_fs_pb2
from grr_response_proto.rrg import os_pb2 as rrg_os_pb2


class PurePosixPathTest(absltest.TestCase):

  def testInitStr(self):
    self.assertEqual(
        rrg_path.PurePosixPath("/foo/bar/baz"),
        pathlib.PurePosixPath("/foo/bar/baz"),
    )

  def testInitPath(self):
    self.assertEqual(
        rrg_path.PurePosixPath(pathlib.PurePosixPath("/foo/bar/baz")),
        pathlib.PurePosixPath("/foo/bar/baz"),
    )

  def testInitMultiple(self):
    self.assertEqual(
        rrg_path.PurePosixPath("/foo", "bar", "baz"),
        pathlib.PurePosixPath("/foo/bar/baz"),
    )

  def testAscii(self):
    path = rrg_fs_pb2.Path()
    path.raw_bytes = "/foo/bar/baz".encode("ascii")

    self.assertEqual(
        rrg_path.PurePosixPath(path),
        pathlib.PurePosixPath("/foo/bar/baz"),
    )

  def testUnicode(self):
    path = rrg_fs_pb2.Path()
    path.raw_bytes = "/zażółć/gęślą/jaźń".encode("utf-8")

    self.assertEqual(
        rrg_path.PurePosixPath(path),
        pathlib.PurePosixPath("/zażółć/gęślą/jaźń"),
    )

  def testBytes(self):
    path = rrg_fs_pb2.Path()
    path.raw_bytes = b"/\xffoo/bar/\xbb\xaar"

    self.assertEqual(
        rrg_path.PurePosixPath(path),
        pathlib.PurePosixPath(r"/\xffoo/bar/\xbb\xaar"),
    )

  def testComponents(self):
    path = rrg_fs_pb2.Path()
    path.raw_bytes = "/foo/bar/baz".encode("ascii")

    self.assertEqual(
        rrg_path.PurePosixPath(path).components,
        ("foo", "bar", "baz"),
    )

  def testComponents_Bytes(self):
    path = rrg_fs_pb2.Path()
    path.raw_bytes = b"/\xffoo/bar/\xbb\xaar"

    self.assertEqual(
        rrg_path.PurePosixPath(path).components,
        ("\\xffoo", "bar", "\\xbb\\xaar"),
    )

  def testComponents_Root(self):
    path = rrg_fs_pb2.Path()
    path.raw_bytes = "/".encode("ascii")

    self.assertEqual(
        rrg_path.PurePosixPath(path).components,
        (),
    )

  def testComponents_Relative(self):
    path = rrg_fs_pb2.Path()
    path.raw_bytes = "foo/bar".encode("ascii")

    with self.assertRaises(ValueError):
      _ = rrg_path.PurePosixPath(path).components

  def testNormal_Dot(self):
    self.assertEqual(
        rrg_path.PurePosixPath("/foo/bar/./baz").normal,
        rrg_path.PurePosixPath("/foo/bar/baz"),
    )

  def testNormal_Parent(self):
    self.assertEqual(
        rrg_path.PurePosixPath("/foo/bar/../baz").normal,
        rrg_path.PurePosixPath("/foo/baz"),
    )


class PureWindowsPathTest(absltest.TestCase):

  def testInitStr(self):
    self.assertEqual(
        rrg_path.PureWindowsPath(r"X:\Foo Bar\Quux"),
        pathlib.PureWindowsPath(r"X:\Foo Bar\Quux"),
    )

  def testInitPath(self):
    self.assertEqual(
        rrg_path.PureWindowsPath(pathlib.PureWindowsPath(r"X:\Foo Bar\Quux")),
        pathlib.PureWindowsPath(r"X:\Foo Bar\Quux"),
    )

  def testInitMultiple(self):
    self.assertEqual(
        rrg_path.PureWindowsPath("X:\\", "Foo Bar", "Quux"),
        pathlib.PureWindowsPath(r"X:\Foo Bar\Quux"),
    )

  def testAscii(self):
    path = rrg_fs_pb2.Path()
    path.raw_bytes = r"X:\Foo Bar\Quux".encode("ascii")

    self.assertEqual(
        rrg_path.PureWindowsPath(path),
        pathlib.PureWindowsPath(r"X:\Foo Bar\Quux"),
    )

  def testUnicode(self):
    path = rrg_fs_pb2.Path()
    path.raw_bytes = r"X:\Zażółć\Gęślą Jaźń".encode("utf-8")

    self.assertEqual(
        rrg_path.PureWindowsPath(path),
        pathlib.PureWindowsPath(r"X:\Zażółć\Gęślą Jaźń"),
    )

  def testUnpairedSurrogate(self):
    path = rrg_fs_pb2.Path()
    path.raw_bytes = b"X:\\Foo Bar\\\xed\xa0\x80"

    self.assertEqual(
        rrg_path.PureWindowsPath(path),
        pathlib.PureWindowsPath("X:\\Foo Bar\\���"),
    )

  def testComponents(self):
    path = rrg_fs_pb2.Path()
    path.raw_bytes = r"X:\Foo Bar\Quux".encode("ascii")

    self.assertEqual(
        rrg_path.PureWindowsPath(path).components,
        ("X:", "Foo Bar", "Quux"),
    )

  def testComponents_UnpairedSurrogate(self):
    path = rrg_fs_pb2.Path()
    path.raw_bytes = b"X:\\Foo Bar\\\xed\xa0\x80"

    self.assertEqual(
        rrg_path.PureWindowsPath(path).components,
        ("X:", "Foo Bar", "���"),
    )

  def testComponents_Drive(self):
    path = rrg_fs_pb2.Path()
    path.raw_bytes = b"X:\\"

    self.assertEqual(
        rrg_path.PureWindowsPath(path).components,
        ("X:",),
    )

  def testComponents_Relative(self):
    path = rrg_fs_pb2.Path()
    path.raw_bytes = r"Foo Bar\Quux".encode("ascii")

    with self.assertRaises(ValueError):
      _ = rrg_path.PureWindowsPath(path).components

  def testNormal_Dot(self):
    self.assertEqual(
        rrg_path.PureWindowsPath(r"X:\Foo\Bar\.\Baz").normal,
        rrg_path.PureWindowsPath(r"X:\Foo\Bar\Baz"),
    )

  def testNormal_Parent(self):
    self.assertEqual(
        rrg_path.PureWindowsPath(r"X:\Foo\Bar\..\Baz").normal,
        rrg_path.PureWindowsPath(r"X:\Foo\Baz"),
    )


class PurePathTest(absltest.TestCase):

  def testFor_Linux(self):
    path = rrg_fs_pb2.Path()
    path.raw_bytes = b"/\xffoo/bar/\xbb\xaar"

    self.assertEqual(
        rrg_path.PurePath.For(rrg_os_pb2.LINUX, path),
        pathlib.PurePosixPath(r"/\xffoo/bar/\xbb\xaar"),
    )

  def testFor_Macos(self):
    path = rrg_fs_pb2.Path()
    path.raw_bytes = "/zażółć/gęślą/jaźń".encode("utf-8")

    self.assertEqual(
        rrg_path.PurePath.For(rrg_os_pb2.MACOS, path),
        pathlib.PurePosixPath("/zażółć/gęślą/jaźń"),
    )

  def testFor_Windows(self):
    path = rrg_fs_pb2.Path()
    path.raw_bytes = r"X:\Zażółć\Gęślą Jaźń".encode("utf-8")

    self.assertEqual(
        rrg_path.PurePath.For(rrg_os_pb2.WINDOWS, path),
        pathlib.PureWindowsPath(r"X:\Zażółć\Gęślą Jaźń"),
    )


if __name__ == "__main__":
  absltest.main()
