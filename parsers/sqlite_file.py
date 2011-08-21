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


"""Parser for sqlite database files."""




import os
import tempfile


from sqlite3 import dbapi2 as sqlite

import logging


class SQLiteFile(object):
  """Class for handling the parsing sqlite database files.

    Use as:
      c = SQLiteFile(open('filename.db'))
      for hist in c.Parse():
        print hist
  """

  def __init__(self, file_object, delete_tempfile=True):
    """Init.

    Args:
      file_object: A file like object.
      delete_tempfile: If we create a tempfile, should we delete it when
        we're done.
    """
    self.file_object = file_object

    # We want to be able to read from arbitrary file like objects
    # but sqlite lib doesn't support this so we need to write out
    # to a tempfile.
    if hasattr(self.file_object, "name"):
      self.name = self.file_object.name
      self._delete_file = False
    else:
      self._delete_file = delete_tempfile
      with tempfile.NamedTemporaryFile(delete=False) as fd:
        self.name = fd.name
        data = file_object.read(65536)
        while data:
          fd.write(data)
          data = file_object.read(65536)

  def __del__(self):
    """Deletes the database file."""
    if self._delete_file:
      try:
        os.remove(self.name)
      except (OSError, IOError):
        pass

  def Query(self, sql_query):
    """Query the database file."""
    results = {}

    try:
      self._connection = sqlite.connect(self.name)
      self._cursor = self._connection.cursor()
      results = self._cursor.execute(sql_query).fetchall()

    except sqlite.Error, error_string:
      logging.warn("SQLite error %s", error_string)

    return results

