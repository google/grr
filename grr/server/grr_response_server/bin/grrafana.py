#!/usr/bin/env python
# Lint as: python3
from absl import app, flags
import collections
import json
import os
from typing import Any, cast, Dict, List, Text, Tuple, Iterable

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
from werkzeug import wsgi as werkzeug_wsgi
from werkzeug.wrappers import json as werkzeug_wrappers_json

AVAILABLE_METRICS = [
    "mean_user_cpu_rate",
    "max_user_cpu_rate",
    "mean_system_cpu_rate",
    "max_system_cpu_rate",
    "mean_resident_memory_mib",
    "max_resident_memory_mib",
]

JSON_MIME_TYPE = "application/json"

flags.DEFINE_bool(
    "version",
    default=False,
    allow_override=True,
    help="Print the GRR console version number and exit immediately.")


class JSONRequest(werkzeug_wrappers_json.JSONMixin, werkzeug_wrappers.Request):
  pass


class JSONResponse(werkzeug_wrappers_json.JSONMixin,
                   werkzeug_wrappers.Response):

  def __init__(self, *args, **kwargs) -> None:
    kwargs["mimetype"] = JSON_MIME_TYPE
    response = kwargs.get("response")
    if response and not isinstance(response, werkzeug_wsgi.ClosingIterator):
      kwargs["response"] = json.dumps(response)
    super().__init__(*args, **kwargs)


class Grrafana(object):
  """GRRafana HTTP server instance.
  
  A full description of all endpoints implemented within this HTTP
  server can be found in:
  https://github.com/simPod/grafana-json-datasource#api."""

  def __init__(self) -> None:
    """Initializes a new GRRafana HTTP server instance."""
    self._url_map = werkzeug_routing.Map([
        werkzeug_routing.Rule("/", endpoint=self._OnRoot, methods=["GET"]),
        werkzeug_routing.Rule("/search",
                              endpoint=self._OnSearch,
                              methods=["POST"]),
        werkzeug_routing.Rule("/query",
                              endpoint=self._OnQuery,
                              methods=["POST"]),
        werkzeug_routing.Rule("/annotations",
                              endpoint=self._OnAnnotations,
                              methods=["POST"]),
    ])

  def _DispatchRequest(self, request: JSONRequest) -> JSONResponse:
    """Maps requests to different methods."""
    adapter = self._url_map.bind_to_environ(request.environ)
    try:
      endpoint, values = adapter.match()
      return endpoint(request, **values)
    except werkzeug_exceptions.HTTPException as e:
      return e

  def __call__(self, environ, start_response) -> JSONResponse:
    request = JSONRequest(environ)
    response = self._DispatchRequest(request)
    return response(environ, start_response)

  def _OnRoot(self, request: JSONRequest) -> JSONResponse:
    """Returns OK message to database connection check."""
    return JSONResponse()

  def _OnSearch(self, request: JSONRequest) -> JSONResponse:
    """Fetches available resource usage metrics.
    
    Depending on the type of request Grafana is issuing, this method returns
    either available client resource usage metrics from the constant 
    AVAILABLE_METRICS, or possible values for a defined Grafana variable."""
    if "type" in request.json:
      # Grafana request issued on Panel > Queries page. Grafana expects the
      # list of metrics that can be listed on the dropdown-menu
      # called "Metric".
      response = AVAILABLE_METRICS
    else:
      # Grafana request issued on Variables > New/Edit page for variables of
      # type query. Grafana expectes the list of possible values of
      # the variable. At the moment, GRRafana doesn't support such variables,
      # so it returns no possible values.
      response = []
    return JSONResponse(response=response)

  def _OnQuery(self, request: JSONRequest) -> JSONResponse:
    """Retrieves datapoints for Grafana.
    
    Given a client ID as a Grafana variable and targets (resource usages),
    returns datapoints in a format Grafana can interpret."""
    json_data = request.json
    requested_client_id = _ExtractClientIdFromVariable(
        json_data)  # There must be a ClientID variable declated in Grafana.
    requested_targets = [entry["target"] for entry in json_data["targets"]]
    list_targets_with_datapoints = _FetchDatapointsForTargets(requested_client_id,
                                          json_data["maxDataPoints"],
                                          requested_targets)
    response = [t._asdict() for t in list_targets_with_datapoints]
    return JSONResponse(response=response)

  def _OnAnnotations(self, request: JSONRequest) -> JSONResponse:
    pass


_Datapoint = Tuple[float, int]
_Datapoints = List[_Datapoint]
_TargetWithDatapoints = collections.namedtuple("TargetWithDatapoints",
                                              ["target", "datapoints"])


def _FetchDatapointsForTargets(
    client_id: Text, limit: int,
    targets: Iterable[Text]) -> List[_TargetWithDatapoints]:
  """Fetches a list of <datapoint, timestamp> tuples for each target 
  metric from Fleetspeak database."""
  records_list = fleetspeak_utils.FetchClientResourceUsageRecords(
      client_id, limit)
  response = []
  for target in targets:
    datapoints_for_single_target = _CreateDatapointsForTarget(
        target, records_list)
    response.append(
        _TargetWithDatapoints(target=target,
                             datapoints=datapoints_for_single_target))
  return response


def _CreateDatapointsForTarget(
    target: Text,
    records_list: Iterable[resource_pb2.ClientResourceUsageRecord]
) -> _Datapoints:
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
  else:
    raise NameError(
        f"Target {target} is not a resource usage metric that can be " \
         "fetched from Fleetspeak."
    )
  return [
      (v,
      r.server_timestamp.seconds * 1000 + r.server_timestamp.nanos // 1000000)
      for (v, r) in zip(record_values, records_list)
  ]


def _ExtractClientIdFromVariable(req: JSONRequest) -> Text:
  """Extracts the client ID from a Grafana JSON request."""
  return req["scopedVars"]["ClientID"]["value"]


def main(argv: Any) -> None:
  """Main."""
  del argv  # Unused.

  if flags.FLAGS.version:
    print(f"GRRafana server {config_server.VERSION['packageversion']}")
    return

  config.CONFIG.AddContext(contexts.GRRAFANA_CONTEXT,
                           "Context applied when running GRRafana server.")
  server_startup.Init()
  fleetspeak_connector.Init()
  werkzeug_serving.run_simple("127.0.0.1",
                              5000,
                              Grrafana(),
                              use_debugger=True,
                              use_reloader=True)


if __name__ == "__main__":
  app.run(main)
