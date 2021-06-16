#!/usr/bin/env python

import io
import os

from absl.testing import absltest

from grr_response_core.lib.util import temp
from grr.test_lib import filesystem_test_lib


class CreateFileTest(absltest.TestCase):

  def testDefault(self):
    with temp.AutoTempDirPath(remove_non_empty=True) as dirpath:
      filepath = os.path.join(dirpath, "foo")

      filesystem_test_lib.CreateFile(filepath)
      self.assertTrue(os.path.exists(filepath))

  def testContents(self):
    with temp.AutoTempDirPath(remove_non_empty=True) as dirpath:
      filepath = os.path.join(dirpath, "foo")

      filesystem_test_lib.CreateFile(filepath, content=b"foobarbaz")

      with io.open(filepath, "rb") as filedesc:
        content = filedesc.read()

      self.assertEqual(content, b"foobarbaz")

  def testPathCreation(self):
    with temp.AutoTempDirPath(remove_non_empty=True) as dirpath:
      filepath = os.path.join(dirpath, "foo", "bar", "baz")

      filesystem_test_lib.CreateFile(filepath)
      self.assertTrue(os.path.exists(filepath))


if __name__ == "__main__":
  absltest.main()
