#!/usr/bin/env python
"""A module with compatibility wrappers for CSV processing."""
from __future__ import absolute_import
from __future__ import division

from __future__ import unicode_literals

import csv
import io

from future.builtins import str as text
from typing import Iterator, Dict, List, Text

from grr_response_core.lib.util import compatibility
from grr_response_core.lib.util import precondition


class Reader(object):
  """A compatibility class for reading CSV files.

  This class should be used instead of the `csv.reader` that has API differences
  across Python 2 and Python 3. This class provides unified interface that
  should work the same way on both versions. Once support for Python 2 is
  dropped, this class can be removed and code can be refactored to use the
  native class.

  Args:
    delimiter: A delimiter the values are separated with. Defaults to a comma.
  """

  def __init__(self, content, delimiter = ","):
    precondition.AssertType(content, text)
    precondition.AssertType(delimiter, text)

    self._content = content
    self._delimiter = delimiter

  def __iter__(self):
    if compatibility.PY2:
      filedesc = io.BytesIO(self._content.encode("utf-8"))
    else:
      filedesc = io.StringIO(self._content)

    reader = csv.reader(
        filedesc, delimiter=str(self._delimiter), lineterminator=str("\n"))

    for values in reader:
      row = []

      for value in values:
        if compatibility.PY2:
          # TODO(hanuszczak): https://github.com/google/pytype/issues/127
          row.append(value.decode("utf-8"))  # pytype: disable=attribute-error
        else:
          row.append(value)

      yield row


class Writer(object):
  """A compatibility class for writing CSV files.

  This class should be used instead of the `csv.writer` that has API differences
  across Python 2 and Python 3. This class provides unified interface that
  should work the same way on both versions. Once support for Python 2 is
  dropped, this class can be removed and code can be refactored to use the
  native class.

  Args:
    delimiter: A delimiter to separate the values with. Defaults to a comma.
  """

  def __init__(self, delimiter = ","):
    precondition.AssertType(delimiter, text)

    if compatibility.PY2:
      self._output = io.BytesIO()
    else:
      self._output = io.StringIO()

    # We call `str` on the delimiter in order to ensure it is `bytes` on Python
    # 2 and `unicode` on Python 3.
    self._csv = csv.writer(
        self._output, delimiter=str(delimiter), lineterminator=str("\n"))

  def WriteRow(self, values):
    """Writes a single row to the underlying buffer.

    Args:
      values: A list of string values to be inserted into the CSV output.
    """
    precondition.AssertIterableType(values, text)

    if compatibility.PY2:
      self._csv.writerow([value.encode("utf-8") for value in values])
    else:
      self._csv.writerow(values)

  def Content(self):
    if compatibility.PY2:
      # TODO(hanuszczak): https://github.com/google/pytype/issues/127
      return self._output.getvalue().decode("utf-8")  # pytype: disable=attribute-error
    else:
      return self._output.getvalue()  # pytype: disable=bad-return-type


class DictWriter(object):
  """A compatibility class for writing CSV files.

  This class is to `csv.DictWriter` what `CsvWriter` is `csv.writer`. Consult
  documentation for `CsvWriter` for more rationale.

  Args:
    columns: A list of column names to base row writing on.
    delimiter: A delimiter to separate the values with. Defaults to a comma.
  """

  def __init__(self, columns, delimiter = ","):
    precondition.AssertIterableType(columns, text)
    precondition.AssertType(delimiter, text)

    self._writer = Writer(delimiter=delimiter)
    self._columns = columns

  def WriteHeader(self):
    """Writes header to the CSV file.

    A header consist of column names of this particular writer separated by
    specified delimiter.
    """
    self._writer.WriteRow(self._columns)

  def WriteRow(self, values):
    """Writes a single row to the underlying buffer.

    Args:
      values: A dictionary mapping column names to values to be inserted into
        the CSV output.
    """
    precondition.AssertDictType(values, text, text)

    row = []
    for column in self._columns:
      try:
        value = values[column]
      except KeyError:
        raise ValueError("Row does not contain required column `%s`" % column)

      row.append(value)

    self._writer.WriteRow(row)

  def Content(self):
    return self._writer.Content()
