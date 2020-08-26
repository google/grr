#!/usr/bin/env python
# Lint as: python3
import os
import json
import typing
from typing import Any, List, Tuple, Dict, Text

from werkzeug.wrappers import Request, Response
from werkzeug.wrappers.json import JSONMixin
from werkzeug.routing import Map, Rule
from werkzeug.exceptions import HTTPException, NotFound
from werkzeug.middleware.shared_data import SharedDataMiddleware
from werkzeug.utils import redirect
from werkzeug.serving import run_simple

from absl import app
from absl import flags

from grr_response_core.config import server as config_server
from grr_response_server import fleetspeak_connector
from grr_response_server import fleetspeak_utils
from grr_response_server import server_startup
from grr_response_core import config
from grr_response_core.config import contexts

from fleetspeak.src.server.proto.fleetspeak_server.resource_pb2 import ClientResourceUsageRecord


AVAILABLE_METRICS = ['mean_user_cpu_rate', 'max_user_cpu_rate', 'mean_system_cpu_rate', 
                    'max_system_cpu_rate', 'mean_resident_memory_mib', 'max_resident_memory_mib']

flags.DEFINE_bool(
  "version",
  default=False,
  allow_override=True,
  help="Print the GRR console version number and exit immediately.")


class JSONRequest(JSONMixin, Request):
  pass


class JSONResponse(JSONMixin, Response):
  pass


class Grrafana(object):
  """GRRafana HTTP server instance.
  
  A full description of all endpoints implemented within this HTTP
  server can be found in https://github.com/simPod/grafana-json-datasource#api."""

  def __init__(self, config: dict) -> None:
    """Constructor."""
    self.url_map = Map([
    Rule('/', endpoint='Root', methods=["GET"]),
    Rule('/search', endpoint='Search', methods=["POST"]),
    Rule('/query', endpoint='Query', methods=["POST"]),
    Rule('/annotations', endpoint='Annotations', methods=["POST"])
    ])

  def dispatchRequest(self, request: JSONRequest) -> Any:
    """Maps requests to different methods."""
    adapter = self.url_map.bind_to_environ(request.environ)
    try:
      endpoint, values = adapter.match()
      return getattr(self, 'on' + endpoint)(request, **values)
    except HTTPException as e:
      return e

  def wsgiApp(self, environ, start_response) -> Response:
    request = JSONRequest(environ)
    response = self.dispatchRequest(request)
    return response(environ, start_response)

  def __call__(self, environ, start_response):
    return self.wsgiApp(environ, start_response)

  def onRoot(self, request: JSONRequest) -> JSONResponse:
    """Returns OK message to database connection check."""
    return JSONResponse()

  def onSearch(self, request: JSONRequest) -> JSONResponse:
    """Depending on the request type, returns either available client
    resource usage metrics from Fleetspeak database, or possible values
    for a defined Grafana variable (currently supports only variables based
    on client IDs)."""
    if "type" in request.json:
      # Request issued on Panel > Queries page.
      response = AVAILABLE_METRICS
    else:
      # Grafana issued request on Variables > New/Edit page.
      response = fetchClientIds()  # todo: support Grafana variables other than ClientID.
    return JSONResponse(response=json.dumps(response), mimetype="application/json")

  def onQuery(self, request: JSONRequest) -> JSONResponse:
    """Given a client ID as a Grafana variable and targets (resource usages),
    returns datapoints in a format Grafana can interpret."""
    request_json_format = request.json
    requested_client_id = extractClientIdFromVariable(request_json_format)  # There must be a ClientID variable declated in Grafana.
    requested_targets = [entry["target"] for entry in request_json_format["targets"]]
    response = fetchDatapointsForTargets(requested_client_id, request_json_format["maxDataPoints"], requested_targets)
    return JSONResponse(response=json.dumps(response), mimetype="application/json")

  def onAnnotations(self, request: JSONRequest) -> JSONResponse:
    pass


def fetchClientIds() -> List[Text]:
  """Fetches GRR client IDs that have resource usage records in Fleetspeak database."""
  return fleetspeak_utils.GetClientIdsFromFleetspeak()


Datapoint = Tuple[float, int]
Datapoints = List[Datapoint]
TargetWithDatapoints = Dict[Text, Datapoints]
def fetchDatapointsForTargets(client_id: Text, limit: int, targets: List[Text]) -> List[TargetWithDatapoints]:
  """Fetches a list of <datapoint, timestamp> tuples for each target metric from Fleetspeak database."""
  records_list = fleetspeak_utils.FetchClientResourceUsageRecordsFromFleetspeak(client_id, limit)
  response = list()
  for target in targets:
    datapoints_for_single_target = createDatapointsForTarget(target, records_list)
    target_datapoints_dict = typing.cast(TargetWithDatapoints, {"target": target, "datapoints": datapoints_for_single_target})
    response.append(target_datapoints_dict)
  return response


def createDatapointsForTarget(target: Text, records_list: List[ClientResourceUsageRecord]) -> Datapoints:
  if target == "mean_user_cpu_rate":
    record_values = [record.mean_user_cpu_rate for record in records_list]
  elif target == "max_user_cpu_rate":
    record_values = [record.max_user_cpu_rate for record in records_list]
  elif target == "mean_system_cpu_rate":
    record_values = [record.mean_system_cpu_rate for record in records_list]
  elif target == "max_system_cpu_rate":
    record_values = [record.max_system_cpu_rate for record in records_list]
  elif target == "mean_resident_memory_mib":
    record_values = [record.mean_resident_memory_mib for record in records_list]
  elif target == "max_resident_memory_mib":
    record_values = [record.max_resident_memory_mib for record in records_list]
  return [(v, r.server_timestamp.seconds * 1000) for (v, r) in zip(record_values, records_list)]


def extractClientIdFromVariable(req: JSONRequest) -> Text:
  """Extracts the client ID from a Grafana JSON request."""
  # Based on an assumption that there is only one Grafana variable.
  return next(iter(req["scopedVars"].values()))["value"]


def main(argv: Any) -> None:
  """Main."""
  del argv  # Unused.

  if flags.FLAGS.version:
    print("GRRafana server {}".format(config_server.VERSION["packageversion"]))
    return
  
  config.CONFIG.AddContext(contexts.GRRAFANA_CONTEXT, "Context applied when running GRRafana server.")
  server_startup.Init()
  fleetspeak_connector.Init()
  run_simple('127.0.0.1', 5000, Grrafana({}), use_debugger=True, use_reloader=True)


if __name__ == '__main__':
  app.run(main)
