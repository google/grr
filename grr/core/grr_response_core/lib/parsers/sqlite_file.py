#!/usr/bin/env python
"""Parser for sqlite database files."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import logging
import os
import tempfile


from sqlite3 import dbapi2 as sqlite


class SQLiteFile(object):
  """Class for handling the parsing sqlite database files.

    Use as:
      c = SQLiteFile(open('filename.db'))
      for row in c.Query(sql_query):
        print row

    The journal_mode parameter controls the "Write-Ahead Log"
    introduced in recent SQLite versions. If set to "WAL", this log is
    used to save transaction data and can bring performance
    improvements. It does, however, require write permissions to the
    directory the database resides in since it creates the log file
    there. This can lead to problems with unit tests so we disable by
    default since we are mostly using the database in read only mode
    anyways.

  """

  def __init__(self, file_object, delete_tempfile=True, journal_mode="DELETE"):
    """Init.

    Args:
      file_object: A file like object.
      delete_tempfile: If we create a tempfile, should we delete it when
        we're done.
      journal_mode: If set to "WAL" a "Write-Ahead Log" is created.
    """
    self.file_object = file_object
    self.journal_mode = journal_mode

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
      self._connection.execute("PRAGMA journal_mode=%s" % self.journal_mode)
      self._cursor = self._connection.cursor()
      results = self._cursor.execute(sql_query).fetchall()

    except sqlite.Error as error_string:
      logging.warn("SQLite error %s", error_string)

    return results
