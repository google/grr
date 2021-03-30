#!/usr/bin/env python
from absl.testing import absltest

from grr_colab._textify import stat
from grr_response_proto import jobs_pb2


class IconTest(absltest.TestCase):

  def testDirectory(self):
    entry = jobs_pb2.StatEntry()
    entry.st_mode = 16877

    self.assertEqual(stat.icon(entry), '📂')

  def testSymlinkMode(self):
    entry = jobs_pb2.StatEntry()
    entry.st_mode = 41471

    self.assertEqual(stat.icon(entry), '🔗')

  def testSymlinkPath(self):
    entry = jobs_pb2.StatEntry()
    entry.st_mode = 33188
    entry.symlink = 'foobar'

    self.assertEqual(stat.icon(entry), '🔗')

  def testFile(self):
    entry = jobs_pb2.StatEntry()
    entry.st_mode = 33188

    self.assertEqual(stat.icon(entry), '📄')


class NameTest(absltest.TestCase):

  def testFile(self):
    entry = jobs_pb2.StatEntry()
    entry.pathspec.path = 'foo'
    entry.st_mode = 33188

    self.assertEqual(stat.name(entry), 'foo')

  def testSymlink(self):
    entry = jobs_pb2.StatEntry()
    entry.pathspec.path = 'foo'
    entry.symlink = 'bar'

    self.assertEqual(stat.name(entry), 'foo -> bar')


class ModeTest(absltest.TestCase):

  def testSymlink(self):
    entry = jobs_pb2.StatEntry()
    entry.st_mode = 41471

    self.assertEqual(stat.mode(entry), 'lrwxrwxrwx')

  def testSuidFile(self):
    entry = jobs_pb2.StatEntry()
    entry.st_mode = 36772

    self.assertEqual(stat.mode(entry), '-rwSr-Sr-T')

  def testFileNoPermissions(self):
    entry = jobs_pb2.StatEntry()
    entry.st_mode = 32768

    self.assertEqual(stat.mode(entry), '----------')

  def testFileAllPermissions(self):
    entry = jobs_pb2.StatEntry()
    entry.st_mode = 33279

    self.assertEqual(stat.mode(entry), '-rwxrwxrwx')


if __name__ == '__main__':
  absltest.main()
