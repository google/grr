#!/usr/bin/env python
# Lint as: python3
"""A module with API handlers related to the Osquery flow."""
import csv
import io

from typing import Iterable
from typing import Iterator
from typing import Optional
from typing import Text

from grr_response_core.lib.rdfvalues import osquery as rdf_osquery
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto.api import osquery_pb2 as api_osquery_pb2
from grr_response_server import data_store
from grr_response_server.flows.general import osquery
from grr_response_server.gui import api_call_context
from grr_response_server.gui import api_call_handler_base
from grr_response_server.gui.api_plugins import client as api_client
from grr_response_server.gui.api_plugins import flow as api_flow


class ApiGetOsqueryResultsArgs(rdf_structs.RDFProtoStruct):
  """An RDF wrapper class for the arguments of Osquery exporter."""

  protobuf = api_osquery_pb2.ApiGetOsqueryResultsArgs
  rdf_deps = [
      api_client.ApiClientId,
      api_flow.ApiFlowId,
  ]


class ApiGetOsqueryResultsHandler(api_call_handler_base.ApiCallHandler):
  """An API handler for the timeline exporter."""

  args_type = ApiGetOsqueryResultsArgs

  def Handle(
      self,
      args: ApiGetOsqueryResultsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_call_handler_base.ApiBinaryStream:
    """Handles requests for the exporting of Osquery flow results."""
    client_id = str(args.client_id)
    flow_id = str(args.flow_id)

    flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
    if flow_obj.flow_class_name != osquery.OsqueryFlow.__name__:
      message = f"Flow '{flow_id}' is not an Osquery flow"
      raise ValueError(message)

    if args.format == ApiGetOsqueryResultsArgs.Format.CSV:  # pytype: disable=attribute-error
      return _StreamCsv(client_id=client_id, flow_id=flow_id)

    message = f"Incorrect Osquery results export format: {args.format}"
    raise ValueError(message)


def _StreamCsv(
    client_id: Text,
    flow_id: Text,
) -> api_call_handler_base.ApiBinaryStream:
  filename = f"osquery_{flow_id}.csv"

  results = _FetchOsqueryResults(client_id=client_id, flow_id=flow_id)
  content = _ParseToCsvBytes(results)

  return api_call_handler_base.ApiBinaryStream(filename, content)


def _FetchOsqueryResults(
    client_id: Text,
    flow_id: Text,
) -> Iterator[rdf_osquery.OsqueryResult]:
  """Fetches results for given client and flow ids."""
  next_to_fetch = 0
  last_fetched_count = None

  while last_fetched_count != 0:
    data_fetched = data_store.REL_DB.ReadFlowResults(
        offset=next_to_fetch,
        count=_RESULTS_TO_FETCH_AT_ONCE,
        client_id=client_id,
        flow_id=flow_id)

    last_fetched_count = len(data_fetched)
    next_to_fetch += last_fetched_count

    for datum in data_fetched:
      if not isinstance(datum.payload, rdf_osquery.OsqueryResult):
        raise ValueError(f"Incorrect payload type: {type(datum.payload)}")
      yield datum.payload


def _ParseToCsvBytes(
    osquery_results: Iterator[rdf_osquery.OsqueryResult],) -> Iterator[bytes]:
  """Parses osquery results into chunks of bytes."""
  added_columns = False

  for result in osquery_results:
    if not added_columns:
      added_columns = True
      columns = result.GetTableColumns()
      yield _LineToCsvBytes(columns)

    yield from map(_LineToCsvBytes, result.GetTableRows())


def _LineToCsvBytes(values: Iterable[str]) -> bytes:
  # newline='' : https://docs.python.org/3.6/library/csv.html#id3
  with io.StringIO(newline="") as output:
    csv_writer = csv.writer(output)
    csv_writer.writerow(values)

    return output.getvalue().encode("utf-8")


# We aim to hold around ~100MB of results into memory.
# At the moment of writing this, default Osquery.max_chunk_size is 1 MiB.
_RESULTS_TO_FETCH_AT_ONCE = 100
