"""A module with API handlers related to the Osquery flow"""
from grr_response_server.flows.general import osquery
from grr_response_core.lib.rdfvalues import osquery as rdf_osquery

from grr_response_proto.api import osquery_pb2 as api_osquery_pb2
from grr_response_core.lib.rdfvalues import structs as rdf_structs

from grr_response_server.gui import api_call_handler_base
from grr_response_server.gui import api_call_context
from grr_response_server import data_store

from grr_response_server.gui.api_plugins import client as api_client
from grr_response_server.gui.api_plugins import flow as api_flow

from typing import Optional
from typing import Iterator
from typing import Text


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
    print("Handling osquery results request!")

    client_id = str(args.client_id)
    flow_id = str(args.flow_id)

    print(f"Client id: {client_id}, Flow id: {flow_id}")

    flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
    if flow_obj.flow_class_name != osquery.OsqueryFlow.__name__:
      message = f"Flow '{flow_id}' is not an Osquery flow"
      raise ValueError(message)

    if args.format == ApiGetOsqueryResultsArgs.Format.CSV:  # pytype: disable=attribute-error
      return self._StreamCSV(client_id=client_id, flow_id=flow_id)

    message = f"Incorrect Osquery results export format: {args.format}"
    raise ValueError(message)

  def _StreamCSV(
      self,
      client_id: Text,
      flow_id: Text,
  ) -> api_call_handler_base.ApiBinaryStream:
    content = ["col1,col2,col3\ncell11,cell12,cell13\ncell21,cell22,cell23".encode('utf-8')]
    filename = f"osquery_{flow_id}.csv"

    results = data_store.REL_DB.ReadFlowResults(
      client_id=client_id,
      flow_id=flow_id,
      offset=0,
      count=_READ_FLOW_RESULTS_COUNT)

    content = []
    is_first = True

    for result in results:
      osquery_result = result.payload
      if type(osquery_result) != rdf_osquery.OsqueryResult:
        raise ValueError(f"Incorrect result payload: {type(osquery_result)}")

      if is_first:
        columns = [column.name for column in osquery_result.table.header.columns]
        columns_string = ','.join(columns) + '\n'
        columns_bytes = columns_string.encode('utf-8')
        content.append(columns_bytes)

      for row in osquery_result.table.rows:
        cells_string = ','.join(row.values) + '\n'
        cells_bytes = cells_string.encode('utf-8')
        content.append(cells_bytes)

    return api_call_handler_base.ApiBinaryStream(filename, content)


_READ_FLOW_RESULTS_COUNT = 1024 # TODO(simstoykov): Check
