#!/usr/bin/env python
"""A module with client action for talking with osquery."""

from collections.abc import Iterator
import json
import logging
import os
import subprocess
from typing import Any, Optional

from grr_response_client import actions
from grr_response_client.client_actions import tempfiles
from grr_response_core import config
from grr_response_core.lib.rdfvalues import osquery as rdf_osquery
from grr_response_core.lib.util import precondition


class Error(Exception):
  """A class for all osquery-related exceptions."""

  def __init__(self, message: str, cause: Optional[Exception] = None):
    if cause is not None:
      message = "{message}: {cause}".format(message=message, cause=cause)

    super().__init__(message)
    self.cause = cause


# TODO(hanuszczak): Fix the linter error properly.
class TimeoutError(Error):  # pylint: disable=redefined-builtin
  """A class of exceptions raised when a call to osquery timeouts."""

  def __init__(self, cause: Optional[Exception] = None):
    super().__init__("osquery timeout", cause=cause)


class Osquery(actions.ActionPlugin):
  """An action plugin class for talking with osquery."""

  in_rdfvalue = rdf_osquery.OsqueryArgs
  out_rdfvalues = [rdf_osquery.OsqueryResult]

  def Run(self, args: rdf_osquery.OsqueryArgs):
    for result in self.Process(args):
      self.SendReply(result)

  # TODO(hanuszczak): This does not need to be a class method. It should be
  # refactored to a separate function and tested as such.
  def Process(
      self, args: rdf_osquery.OsqueryArgs
  ) -> Iterator[rdf_osquery.OsqueryResult]:
    if not config.CONFIG["Osquery.path"]:
      raise RuntimeError(
          "The `Osquery` action invoked on a client without "
          "osquery path specified."
      )

    if not os.path.exists(config.CONFIG["Osquery.path"]):
      raise RuntimeError(
          "The `Osquery` action invoked on a client where "
          "the specified osquery executable "
          f"({config.CONFIG['Osquery.path']!r}) is not available."
      )

    if not args.query:
      raise ValueError("The `Osquery` was invoked with an empty query.")

    if args.configuration_path and not os.path.exists(args.configuration_path):
      raise ValueError("The configuration path does not exist.")

    output = Query(args)

    json_decoder = json.JSONDecoder(object_pairs_hook=dict)

    table = ParseTable(json_decoder.decode(output))
    table.query = args.query

    for chunk in ChunkTable(table, config.CONFIG["Osquery.max_chunk_size"]):
      yield rdf_osquery.OsqueryResult(table=chunk)


def ChunkTable(
    table: rdf_osquery.OsqueryTable, max_chunk_size: int
) -> Iterator[rdf_osquery.OsqueryTable]:
  """Chunks given table into multiple smaller ones.

  Tables that osquery yields can be arbitrarily large. Because GRR's messages
  cannot be arbitrarily large, it might happen that the table has to be split
  into multiple smaller ones.

  Note that that serialized response protos are going to be slightly bigger than
  the specified limit. For regular values the additional payload should be
  negligible.

  Note that chunking a table that is empty results in no chunks at all.

  Args:
    table: A table to split into multiple smaller ones.
    max_chunk_size: A maximum size of the returned table in bytes.

  Yields:
    Tables with the same query and headers as the input table and a subset of
    rows.
  """

  def ByteLength(string: str) -> int:
    return len(string.encode("utf-8"))

  def Chunk() -> rdf_osquery.OsqueryTable:
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

  # There might be some rows that did not cause the chunk to overflow so it has
  # not been yielded as part of the loop.
  if chunk.rows:
    yield chunk


def ParseTable(table: Any) -> rdf_osquery.OsqueryTable:
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
def ParseHeader(table: Any) -> rdf_osquery.OsqueryHeader:
  """Parses header of osquery output.

  Args:
    table: A table in a "parsed JSON" representation.

  Returns:
    A parsed `rdf_osquery.OsqueryHeader` instance.
  """
  precondition.AssertIterableType(table, dict)

  prototype: list[str] = None

  for row in table:
    columns = list(row.keys())
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


def ParseRow(
    header: rdf_osquery.OsqueryHeader, row: Any
) -> rdf_osquery.OsqueryRow:
  """Parses a single row of osquery output.

  Args:
    header: A parsed header describing the row format.
    row: A row in a "parsed JSON" representation.

  Returns:
    A parsed `rdf_osquery.OsqueryRow` instance.
  """
  precondition.AssertDictType(row, str, str)

  result = rdf_osquery.OsqueryRow()
  for column in header.columns:
    result.values.append(row[column.name])
  return result


def Query(args: rdf_osquery.OsqueryArgs) -> str:
  """Calls osquery with given query and returns its output.

  Args:
    args: A query to call osquery with.

  Returns:
    A "parsed JSON" representation of the osquery output.

  Raises:
    TimeoutError: If a call to the osquery executable times out.
    Error: If anything goes wrong with the subprocess call, including if the
    query is incorrect.
  """
  configuration_path = None

  timeout = args.timeout_millis / 1000  # `subprocess.run` uses seconds.
  try:
    # We use `--S` to enforce shell execution. This is because on Windows there
    # is only `osqueryd` and `osqueryi` is not available. However, by passing
    # `--S` we can make `osqueryd` behave like `osqueryi`. Since this flag also
    # works with `osqueryi`, by passing it we simply expand number of supported
    # executable types.
    command = [
        config.CONFIG["Osquery.path"],
        "--S",  # Enforce shell execution.
        "--logger_stderr=false",  # Only allow errors to be written to stderr.
        "--logger_min_status=3",  # Disable status logs.
        "--logger_min_stderr=2",  # Only ERROR-level logs to stderr.
        "--json",  # Set output format to JSON.
    ]

    if args.configuration_path:
      configuration_path = args.configuration_path
    elif args.configuration_content:
      with tempfiles.CreateGRRTempFile(mode="w+b") as configuration_path_file:
        configuration_path = configuration_path_file.name
        configuration_path_file.write(args.configuration_content.encode())

    if configuration_path:
      command.extend(["--config_path", configuration_path])

    proc = subprocess.run(
        command,
        timeout=timeout,
        check=True,
        input=args.query,
        text=True,
        encoding="utf-8",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
  except subprocess.TimeoutExpired as error:
    raise TimeoutError(cause=error)
  except subprocess.CalledProcessError as error:
    stderr = error.stderr
    raise Error(message=f"Osquery error on the client: {stderr}")
  finally:
    if args.configuration_content and configuration_path:
      try:
        if os.path.exists(configuration_path):
          os.remove(configuration_path)
      except (OSError, IOError) as error:
        logging.error("Failed to remove configuration: %s", error)

  stderr = proc.stderr.strip()
  if stderr:
    # Depending on the version, in case of a syntax error osquery might or might
    # not terminate with a non-zero exit code, but it will always print the
    # error to stderr.
    raise Error(message=f"Osquery error on the client: {stderr}")

  return proc.stdout
