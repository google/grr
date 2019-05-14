#!/usr/bin/env python
"""A module with client action for talking with osquery."""
from __future__ import absolute_import
from __future__ import division

from __future__ import unicode_literals

import collections
import os

from future.builtins import map
from future.utils import iterkeys
from typing import Any
from typing import Iterator
from typing import List
from typing import NamedTuple
from typing import Text

from grr_response_client import actions
from grr_response_core import config
from grr_response_core.lib.rdfvalues import osquery as rdf_osquery
from grr_response_core.lib.util import precondition
from grr_response_core.lib.util.compat import json

# pylint: disable=g-import-not-at-top
try:
  # TODO: `subprocess32` is a backport of Python 3.2+ `subprocess`
  # API. Once support for older versions of Python is dropped, this import can
  # be removed.
  import subprocess32 as subprocess
except ImportError:
  import subprocess
# pylint: enable=g-import-not-at-top


class Error(Exception):
  """A class for all osquery-related exceptions."""

  def __init__(self, message, cause = None):
    if cause is not None:
      message = "{message}: {cause}".format(message=message, cause=cause)

    super(Error, self).__init__(message)
    self.cause = cause


class QueryError(Error):
  """A class of exceptions indicating invalid queries (e.g. syntax errors)."""

  def __init__(self, output, cause = None):
    message = "invalid query: {}".format(output)
    super(QueryError, self).__init__(message, cause=cause)


class TimeoutError(Error):
  """A class of exceptions raised when a call to osquery timeouts."""

  def __init__(self, cause = None):
    super(TimeoutError, self).__init__("osquery timeout", cause=cause)


class Osquery(actions.ActionPlugin):
  """An action plugin class for talking with osquery."""

  in_rdfvalue = rdf_osquery.OsqueryArgs
  out_rdfvalues = [rdf_osquery.OsqueryResult]

  def Run(self, args):
    for result in self.Process(args):
      self.SendReply(result)

  # TODO(hanuszczak): This does not need to be a class method. It should be
  # refactored to a separate function and tested as such.
  def Process(self, args):
    if not config.CONFIG["Osquery.path"]:
      raise RuntimeError("The `Osquery` action invoked on a client without "
                         "osquery path specified.")

    if not os.path.exists(config.CONFIG["Osquery.path"]):
      raise RuntimeError("The `Osquery` action invoked on a client where "
                         "osquery executable is not available.")

    if not args.query:
      raise ValueError("The `Osquery` was invoked with an empty query.")

    output = Query(args)

    # For syntax errors, osquery does not fail (exits with 0) but prints stuff
    # to the standard error.
    if output.stderr and not args.ignore_stderr_errors:
      raise QueryError(output.stderr)

    json_decoder = json.Decoder(object_pairs_hook=collections.OrderedDict)

    table = ParseTable(json_decoder.decode(output.stdout))
    table.query = args.query

    for chunk in ChunkTable(table, config.CONFIG["Osquery.max_chunk_size"]):
      yield rdf_osquery.OsqueryResult(table=chunk, stderr=output.stderr)


def ChunkTable(table,
               max_chunk_size):
  """Chunks given table into multiple smaller ones.

  Tables that osquery yields can be arbitrarily large. Because GRR's messages
  cannot be arbitrarily large, it might happen that the table has to be split
  into multiple smaller ones.

  Note that that serialized response protos are going to be slightly bigger than
  the specified limit. For regular values the additional payload should be
  negligible.

  Args:
    table: A table to split into multiple smaller ones.
    max_chunk_size: A maximum size of the returned table in bytes.

  Yields:
    Tables with the same query and headers as the input table and a subset of
    rows.
  """

  def ByteLength(string):
    return len(string.encode("utf-8"))

  def Chunk():
    result = rdf_osquery.OsqueryTable()
    result.query = table.query
    result.header = table.header
    return result

  chunk = Chunk()
  chunk_size = 0

  for row in table.rows:
    row_size = sum(map(ByteLength, row.values))

    if chunk_size + row_size > max_chunk_size:
      yield chunk

      chunk = Chunk()
      chunk_size = 0

    chunk.rows.append(row)
    chunk_size += row_size

  # We want to yield extra chunk in two cases:
  # * there are some rows that did not cause the chunk to overflow so it has not
  #   been yielded as part of the loop.
  # * the initial table has no rows but we still need to yield some table even
  #   if it is empty.
  if chunk.rows or not table.rows:
    yield chunk


def ParseTable(table):
  """Parses table of osquery output.

  Args:
    table: A table in a "parsed JSON" representation.

  Returns:
    A parsed `rdf_osquery.OsqueryTable` instance.
  """
  precondition.AssertIterableType(table, dict)

  result = rdf_osquery.OsqueryTable()
  result.header = ParseHeader(table)
  for row in table:
    result.rows.append(ParseRow(result.header, row))
  return result


# TODO: Parse type information.
def ParseHeader(table):
  """Parses header of osquery output.

  Args:
    table: A table in a "parsed JSON" representation.

  Returns:
    A parsed `rdf_osquery.OsqueryHeader` instance.
  """
  precondition.AssertIterableType(table, dict)

  prototype = None  # type: List[Text]

  for row in table:
    columns = list(iterkeys(row))
    if prototype is None:
      prototype = columns
    elif prototype != columns:
      message = "Expected columns '{expected}', got '{actual}' for table {json}"
      message = message.format(expected=prototype, actual=columns, json=table)
      raise ValueError(message)

  result = rdf_osquery.OsqueryHeader()
  for name in prototype or []:
    result.columns.append(rdf_osquery.OsqueryColumn(name=name))
  return result


def ParseRow(header,
             row):
  """Parses a single row of osquery output.

  Args:
    header: A parsed header describing the row format.
    row: A row in a "parsed JSON" representation.

  Returns:
    A parsed `rdf_osquery.OsqueryRow` instance.
  """
  precondition.AssertDictType(row, Text, Text)

  result = rdf_osquery.OsqueryRow()
  for column in header.columns:
    result.values.append(row[column.name])
  return result


# TODO(hanuszczak): https://github.com/python/typeshed/issues/2761
ProcOutput = NamedTuple("ProcOutput", [("stdout", Text), ("stderr", Text)])  # pytype: disable=wrong-arg-types


def Query(args):
  """Calls osquery with given query and returns its output.

  Args:
    args: A query to call osquery with.

  Returns:
    A "parsed JSON" representation of the osquery output.

  Raises:
    QueryError: If the query is incorrect.
    TimeoutError: If a call to the osquery executable times out.
    Error: If anything else goes wrong with the subprocess call.
  """
  query = args.query.encode("utf-8")
  timeout = args.timeout_millis / 1000  # `subprocess.run` uses seconds.
  # TODO: pytype is not aware of the backport.
  # pytype: disable=module-attr
  try:
    # We use `--S` to enforce shell execution. This is because on Windows there
    # is only `osqueryd` and `osqueryi` is not available. However, by passing
    # `--S` we can make `osqueryd` behave like `osqueryi`. Since this flag also
    # works with `osqueryi`, by passing it we simply expand number of supported
    # executable types.
    command = [config.CONFIG["Osquery.path"], "--S", "--json", query]
    proc = subprocess.run(
        command,
        timeout=timeout,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
  # TODO: Since we use a backported API, `SubprocessError` is hard
  # to work with. Until support for Python 2 is dropped we re-raise with simpler
  # exception type because we don't really care that much (the exception message
  # should be detailed enough anyway).
  except subprocess.TimeoutExpired as error:
    raise TimeoutError(cause=error)
  except subprocess.CalledProcessError as error:
    raise Error("osquery invocation error", cause=error)
  # pytype: enable=module-attr

  stdout = proc.stdout.decode("utf-8")
  stderr = proc.stderr.decode("utf-8").strip()
  return ProcOutput(stdout=stdout, stderr=stderr)
