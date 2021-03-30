#!/usr/bin/env python
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import io
import os

from absl.testing import absltest

from grr_response_core.lib.util import temp


class TempDirPathTest(absltest.TestCase):

  def testEmptyDirCreation(self):
    dirpath = temp.TempDirPath()

    self.assertTrue(os.path.exists(dirpath))
    self.assertEmpty(os.listdir(dirpath))

    os.rmdir(dirpath)

  def testPrefix(self):
    dirpath = temp.TempDirPath(prefix="foo")

    self.assertTrue(os.path.exists(dirpath))
    self.assertStartsWith(os.path.basename(dirpath), "foo")

    os.rmdir(dirpath)

  def testSuffix(self):
    dirpath = temp.TempDirPath(suffix="foo")

    self.assertTrue(os.path.exists(dirpath))
    self.assertEndsWith(os.path.basename(dirpath), "foo")

    os.rmdir(dirpath)

  def testPrefixAndSuffix(self):
    dirpath = temp.TempDirPath(prefix="foo", suffix="bar")

    self.assertTrue(os.path.exists(dirpath))
    self.assertStartsWith(os.path.basename(dirpath), "foo")
    self.assertEndsWith(os.path.basename(dirpath), "bar")

    os.rmdir(dirpath)


class TempFilePathTest(absltest.TestCase):

  def testEmptyFileCreation(self):
    filepath = temp.TempFilePath()

    self.assertTrue(os.path.exists(filepath))
    with io.open(filepath, "rb") as filedesc:
      self.assertEmpty(filedesc.read())

    os.remove(filepath)

  def testPrefix(self):
    filepath = temp.TempFilePath(prefix="foo")

    self.assertTrue(os.path.exists(filepath))
    self.assertStartsWith(os.path.basename(filepath), "foo")

    os.remove(filepath)

  def testSuffix(self):
    filepath = temp.TempFilePath(suffix="foo")

    self.assertTrue(os.path.exists(filepath))
    self.assertEndsWith(os.path.basename(filepath), "foo")

    os.remove(filepath)

  def testPrefixAndSuffix(self):
    filepath = temp.TempFilePath(prefix="foo", suffix="bar")

    self.assertTrue(os.path.exists(filepath))
    self.assertStartsWith(os.path.basename(filepath), "foo")
    self.assertEndsWith(os.path.basename(filepath), "bar")

    os.remove(filepath)

  def testDir(self):
    with temp.AutoTempDirPath() as dirpath:
      filepath = temp.TempFilePath(dir=dirpath)

      self.assertTrue(os.path.exists(filepath))
      self.assertStartsWith(filepath, dirpath)

      os.remove(filepath)


class AutoTempDirPathTest(absltest.TestCase):

  def testEmptyDirCreation(self):
    with temp.AutoTempDirPath() as dirpath:
      self.assertTrue(os.path.exists(dirpath))
      self.assertEmpty(os.listdir(dirpath))

  def testPrefix(self):
    with temp.AutoTempDirPath(prefix="foo") as dirpath:
      self.assertTrue(os.path.exists(dirpath))
      self.assertStartsWith(os.path.basename(dirpath), "foo")

  def testSuffix(self):
    with temp.AutoTempDirPath(suffix="foo") as dirpath:
      self.assertTrue(os.path.exists(dirpath))
      self.assertEndsWith(os.path.basename(dirpath), "foo")

  def testPrefixAndSuffix(self):
    with temp.AutoTempDirPath(prefix="foo", suffix="bar") as dirpath:
      self.assertTrue(os.path.exists(dirpath))
      self.assertStartsWith(os.path.basename(dirpath), "foo")
      self.assertEndsWith(os.path.basename(dirpath), "bar")

  def testRemovesEmptyDirs(self):
    with temp.AutoTempDirPath() as dirpath:
      self.assertTrue(os.path.exists(dirpath))

    self.assertFalse(os.path.exists(dirpath))

  def testRemovesNonEmptyDirs(self):
    with temp.AutoTempDirPath(remove_non_empty=True) as dirpath:
      self.assertTrue(os.path.exists(dirpath))

      with io.open(os.path.join(dirpath, "foo"), "wb") as filedesc:
        filedesc.write(b"foo")

      with io.open(os.path.join(dirpath, "bar"), "wb") as filedesc:
        filedesc.write(b"bar")

    self.assertFalse(os.path.exists(dirpath))


class AutoTempFilePath(absltest.TestCase):

  def testEmptyFileCreation(self):
    with temp.AutoTempFilePath() as filepath:
      self.assertTrue(os.path.exists(filepath))
      with io.open(filepath, "rb") as filedesc:
        self.assertEmpty(filedesc.read())

  def testPrefix(self):
    with temp.AutoTempFilePath(prefix="foo") as filepath:
      self.assertTrue(os.path.exists(filepath))
      self.assertStartsWith(os.path.basename(filepath), "foo")

  def testSuffix(self):
    with temp.AutoTempFilePath(suffix="foo") as filepath:
      self.assertTrue(os.path.exists(filepath))
      self.assertEndsWith(os.path.basename(filepath), "foo")

  def testPrefixAndSuffix(self):
    with temp.AutoTempFilePath(prefix="foo", suffix="bar") as filepath:
      self.assertTrue(os.path.exists(filepath))
      self.assertStartsWith(os.path.basename(filepath), "foo")
      self.assertEndsWith(os.path.basename(filepath), "bar")

  def testDir(self):
    with temp.AutoTempDirPath() as dirpath:
      with temp.AutoTempFilePath(dir=dirpath) as filepath:
        self.assertTrue(os.path.exists(filepath))
        self.assertStartsWith(filepath, dirpath)

  def testRemovesFiles(self):
    with temp.AutoTempFilePath() as filepath:
      self.assertTrue(os.path.exists(filepath))

    self.assertFalse(os.path.exists(filepath))


if __name__ == "__main__":
  absltest.main()
