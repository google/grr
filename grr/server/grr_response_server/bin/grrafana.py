#!/usr/bin/env python
# Lint as: python3
from absl import app, flags
import json
import os
from typing import Any, cast, Dict, List, Text, Tuple

from fleetspeak.src.server.proto.fleetspeak_server import resource_pb2

from grr_response_core import config
from grr_response_core.config import server as config_server
from grr_response_core.config import contexts
from grr_response_server import fleetspeak_connector
from grr_response_server import fleetspeak_utils
from grr_response_server import server_startup

from werkzeug import exceptions as werkzeug_exceptions
from werkzeug import routing as werkzeug_routing
from werkzeug import serving as werkzeug_serving
from werkzeug import wrappers as werkzeug_wrappers
from werkzeug.wrappers import json as werkzeug_wrappers_json


AVAILABLE_METRICS = [
    'mean_user_cpu_rate',
    'max_user_cpu_rate',
    'mean_system_cpu_rate',
    'max_system_cpu_rate',
    'mean_resident_memory_mib',
    'max_resident_memory_mib',
]
RESPONSE_MIME_TYPE = "application/json"

flags.DEFINE_bool(
    "version",
    default=False,
    allow_override=True,
    help="Print the GRR console version number and exit immediately.")


class JSONRequest(werkzeug_wrappers_json.JSONMixin, werkzeug_wrappers.Request):
  pass


class JSONResponse(werkzeug_wrappers_json.JSONMixin, werkzeug_wrappers.Response):
  pass


class Grrafana(object):
  """GRRafana HTTP server instance.
  
  A full description of all endpoints implemented within this HTTP
  server can be found in https://github.com/simPod/grafana-json-datasource#api."""

  def __init__(self, config: dict) -> None:
    """Constructor."""
    self.url_map = werkzeug_routing.Map([
        werkzeug_routing.Rule('/', endpoint='Root', methods=["GET"]),
        werkzeug_routing.Rule('/search', endpoint='Search', methods=["POST"]),
        werkzeug_routing.Rule('/query', endpoint='Query', methods=["POST"]),
        werkzeug_routing.Rule('/annotations', endpoint='Annotations', methods=["POST"]),
    ])

  def DispatchRequest(self, request: JSONRequest) -> JSONResponse:
    """Maps requests to different methods."""
    adapter = self.url_map.bind_to_environ(request.environ)
    try:
      endpoint, values = adapter.match()
      return getattr(self, 'On' + endpoint)(request, **values)
    except werkzeug_exceptions.HTTPException as e:
      return e

  def WsgiApp(self, environ, start_response) -> werkzeug_wrappers.Response:
    request = JSONRequest(environ)
    response = self.DispatchRequest(request)
    return response(environ, start_response)

  def __call__(self, environ, start_response):
    return self.WsgiApp(environ, start_response)

  def OnRoot(self, request: JSONRequest) -> JSONResponse:
    """Returns OK message to database connection check."""
    return JSONResponse()

  def OnSearch(self, request: JSONRequest) -> JSONResponse:
    """Depending on the type of request Grafana is issuing, this method returns either
    available client resource usage metrics from the constant AVAILABLE_METRICS, or
    possible values for a defined Grafana variable (currently supports only variables based
    on client IDs)."""
    if "type" in request.json:
      # Grafana request issued on Panel > Queries page. Grafana expects the list of metrics
      # that can be listed on the dropdown-menu called "Metric".
      response = AVAILABLE_METRICS
    else:
      # Grafana request issued on Variables > New/Edit page. Grafana expectes the list
      # of possible values of the variable.
      # At the moment, the only Grafana variable we support is ClientID, so only a list
      # of all Fleetspeak client IDs will be returned.
      response = fleetspeak_utils.GetClientIdsFromFleetspeak()
    return JSONResponse(response=json.dumps(response),
                        mimetype=RESPONSE_MIME_TYPE)

  def OnQuery(self, request: JSONRequest) -> JSONResponse:
    """Given a client ID as a Grafana variable and targets (resource usages),
    returns datapoints in a format Grafana can interpret."""
    json_data = request.json
    requested_client_id = _ExtractClientIdFromVariable(
        json_data)  # There must be a ClientID variable declated in Grafana.
    requested_targets = [entry["target"] for entry in json_data["targets"]]
    response = _FetchDatapointsForTargets(requested_client_id,
                                          json_data["maxDataPoints"],
                                          requested_targets)
    return JSONResponse(response=json.dumps(response),
                        mimetype=RESPONSE_MIME_TYPE)

  def OnAnnotations(self, request: JSONRequest) -> JSONResponse:
    pass


Datapoint = Tuple[float, int]
Datapoints = List[Datapoint]
TargetWithDatapoints = Dict[Text, Datapoints]


def _FetchDatapointsForTargets(
    client_id: Text, limit: int,
    targets: List[Text]) -> List[TargetWithDatapoints]:
  """Fetches a list of <datapoint, timestamp> tuples for each target metric from Fleetspeak database."""
  records_list = fleetspeak_utils.FetchClientResourceUsageRecordsFromFleetspeak(
      client_id, limit)
  response = []
  for target in targets:
    datapoints_for_single_target = _CreateDatapointsForTarget(
        target, records_list)
    target_datapoints_dict = cast(TargetWithDatapoints, {
        "target": target,
        "datapoints": datapoints_for_single_target
    })
    response.append(target_datapoints_dict)
  return response


def _CreateDatapointsForTarget(
    target: Text, records_list: List[resource_pb2.ClientResourceUsageRecord]) -> Datapoints:
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
  return [(v, r.server_timestamp.seconds * 1000)
          for (v, r) in zip(record_values, records_list)]


def _ExtractClientIdFromVariable(req: JSONRequest) -> Text:
  """Extracts the client ID from a Grafana JSON request."""
  # Based on an assumption that there is only one Grafana variable.
  scoped_vars_values = list(req["scopedVars"].values())
  return scoped_vars_values[0]["value"]


def main(argv: Any) -> None:
  """Main."""
  del argv  # Unused.

  if flags.FLAGS.version:
    print("GRRafana server {}".format(config_server.VERSION["packageversion"]))
    return

  config.CONFIG.AddContext(contexts.GRRAFANA_CONTEXT,
                           "Context applied when running GRRafana server.")
  server_startup.Init()
  fleetspeak_connector.Init()
  werkzeug_serving.run_simple('127.0.0.1',
             5000,
             Grrafana({}),
             use_debugger=True,
             use_reloader=True)


if __name__ == '__main__':
  app.run(main)
