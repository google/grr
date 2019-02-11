#!/usr/bin/env python
"""A module with client action for talking with osquery."""
from __future__ import absolute_import
from __future__ import division

from __future__ import unicode_literals

import collections
import json
import subprocess

from future.utils import iterkeys
from typing import Any
from typing import List
from typing import Text

from grr_response_client import actions
from grr_response_core import config
from grr_response_core.lib.rdfvalues import osquery as rdf_osquery
from grr_response_core.lib.util import precondition


class Osquery(actions.ActionPlugin):
  """An action plugin class for talking with osquery."""

  in_rdfvalue = rdf_osquery.OsqueryArgs
  out_rdfvalues = [rdf_osquery.OsqueryResult]

  def Run(self, args):
    self.SendReply(self.Process(args))

  # TODO(hanuszczak): This does not need to be a class method. It should be
  # refactored to a separate function and tested as such.
  def Process(self, args):
    if not config.CONFIG["Osquery.path"]:
      raise RuntimeError("The `Osquery` action invoked on a client without "
                         "osquery path specified.")

    result = rdf_osquery.OsqueryResult()

    # TODO: Currently running n-queries involves spawning n osquery
    # processes. This should not be required and needs to be optimized in the
    # future.
    for query in args.queries:
      table = ParseTable(Query(query))
      table.query = query
      result.tables.append(table)

    return result


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


def Query(query):
  """Calls osquery with given query and returns its output.

  Args:
    query: A query to call osquery with.

  Returns:
    A "parsed JSON" representation of the osquery output.

  Raises:
    RuntimeError: If osquery call fails.
  """
  proc = subprocess.Popen([config.CONFIG["Osquery.path"], "--json"],
                          stdin=subprocess.PIPE,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE)
  out, err = proc.communicate(query.encode("utf-8"))
  if err:
    raise RuntimeError("osquery failure: {}".format(err.decode("utf-8")))

  json_decoder = json.JSONDecoder(object_pairs_hook=collections.OrderedDict)
  return json_decoder.decode(out)
