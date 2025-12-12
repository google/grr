#!/usr/bin/env python
"""A module with utility functions for working with SQLite databases."""

from collections.abc import Iterator
import contextlib
import io
import sqlite3
from typing import IO

from grr_response_core.lib.util import temp


class ConnectionContext:
  """A wrapper class around an SQLite connection object.

  This class wraps a low-level SQLite connection that is error-prone and does
  not provide safe context-manager interface.
  """

  def __init__(self, conn: sqlite3.Connection) -> None:
    """Initializes the SQLite connection objects.

    Args:
      conn: A low-level connection to the SQL database.
    """
    self._conn = conn

  def Query(self, query: str) -> Iterator[tuple]:  # pylint: disable=g-bare-generic
    """Queries the underlying database.

    Args:
      query: A query to run.

    Yields:
      Database rows that are results of the query.
    """
    with contextlib.closing(self._conn.cursor()) as cursor:  # pytype: disable=wrong-arg-types
      cursor.execute(query)

      while True:
        rows = cursor.fetchmany(_ROW_FETCH_COUNT)
        if not rows:
          break

        for row in rows:
          yield row


@contextlib.contextmanager
def IOConnection(db_filedesc: IO[bytes]) -> Iterator[ConnectionContext]:
  """A connection to the SQLite database created out of given byte stream.

  Args:
    db_filedesc: A byte stream of the SQLite database file.

  Yields:
    A SQLite connection object that can run queries.
  """
  # SQLite connector can only work with physical database files. Therefore, one
  # needs to dump the contents of the given byte stream to some temporary path.
  with temp.AutoTempFilePath(suffix=".sqlite") as temp_db_filepath:
    with io.open(temp_db_filepath, mode="wb") as temp_db_filedesc:
      _CopyIO(input=db_filedesc, output=temp_db_filedesc)

    with contextlib.closing(sqlite3.connect(temp_db_filepath)) as conn:  # pytype: disable=wrong-arg-types
      yield ConnectionContext(conn)


def _CopyIO(input: IO[bytes], output: IO[bytes]) -> None:  # pylint: disable=redefined-builtin
  """Copies contents of one binary stream into another.

  Args:
    input: An input stream to read from.
    output: An output stream to write to.
  """
  while True:
    buf = input.read(_FILE_BUFFER_SIZE)
    if not buf:
      break

    output.write(buf)


_FILE_BUFFER_SIZE = 1024 * 1024  # 1 MiB.
_ROW_FETCH_COUNT = 1024
