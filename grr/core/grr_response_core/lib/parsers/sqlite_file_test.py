#!/usr/bin/env python
"""Tests for grr.parsers.sqlite_file."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import io
import os

from grr_response_core.lib import flags
from grr_response_core.lib.parsers import sqlite_file
from grr.test_lib import test_lib


class SQLiteFileTest(test_lib.GRRBaseTest):
  """Test parsing of sqlite database files."""

  query = "SELECT * FROM moz_places;"

  def testErrors(self):
    """Test empty files don't raise errors."""
    database_file = sqlite_file.SQLiteFile(io.BytesIO())
    entries = [x for x in database_file.Query(self.query)]
    self.assertEmpty(entries)

  # The places.sqlite contains 92 rows in table moz_places
  def testTmpFiles(self):
    """This should force a write to a tmp file."""
    filename = os.path.join(self.base_path, "places.sqlite")
    with open(filename, "rb") as fd:
      file_stream = io.BytesIO(fd.read())
    database_file = sqlite_file.SQLiteFile(file_stream)
    entries = [x for x in database_file.Query(self.query)]
    self.assertLen(entries, 92)

    # Test the tempfile is deleted
    self.assertEqual(database_file._delete_file, True)
    filename = database_file.name
    self.assertTrue(os.path.exists(filename))
    del database_file
    self.assertFalse(os.path.exists(filename))


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
