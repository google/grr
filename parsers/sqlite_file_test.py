#!/usr/bin/env python
#
# Copyright 2011 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.





import os
import StringIO

from grr.client import conf
from grr.client import conf as flags
from grr.lib import test_lib
from grr.parsers import sqlite_file

FLAGS = flags.FLAGS




class SQLiteFileTest(test_lib.GRRBaseTest):
  """Test parsing of sqlite database files."""

  query = "SELECT * FROM moz_places;"

  def testErrors(self):
    """Test empty files don't raise errors."""
    database_file = sqlite_file.SQLiteFile(StringIO.StringIO())
    entries = [x for x in database_file.Query(self.query)]
    self.assertEquals(len(entries), 0)

  # The places.sqlite contains 92 rows in table moz_places
  def testTmpFiles(self):
    """This should force a write to a tmp file."""
    filename = os.path.join(self.base_path, "places.sqlite")
    file_stream = StringIO.StringIO(open(filename).read())
    database_file = sqlite_file.SQLiteFile(file_stream)
    entries = [x for x in database_file.Query(self.query)]
    self.assertEquals(len(entries), 92)

    # Test the tempfile is deleted
    self.assertEquals(database_file._delete_file, True)
    filename = database_file.name
    self.assertTrue(os.path.exists(filename))
    del database_file
    self.assertFalse(os.path.exists(filename))


def main(argv):
  test_lib.main(argv)

if __name__ == "__main__":
  conf.StartMain(main)

