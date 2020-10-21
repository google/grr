#!/usr/bin/env python
# Lint as: python3
from abc import ABC, abstractmethod
from absl import app, flags
import collections
import dateutil
import json
import os
from typing import Any, Callable, cast, Dict, List, Tuple, Iterable

from fleetspeak.src.server.proto.fleetspeak_server import resource_pb2
from google.protobuf import timestamp_pb2

from grr_response_core import config
from grr_response_core.config import server as config_server
from grr_response_core.config import contexts
from grr_response_server import data_store
from grr_response_server import fleetspeak_connector
from grr_response_server import fleetspeak_utils
from grr_response_server import server_startup

from werkzeug import exceptions as werkzeug_exceptions
from werkzeug import routing as werkzeug_routing
from werkzeug import serving as werkzeug_serving
from werkzeug import wrappers as werkzeug_wrappers
from werkzeug import wsgi as werkzeug_wsgi
from werkzeug.wrappers import json as werkzeug_wrappers_json  # type: ignore


JSON_MIME_TYPE = "application/json"
_FLEET_BREAKDOWN_DAY_BUCKETS = frozenset([1, 7, 14, 30])

flags.DEFINE_bool(
    "version",
    default=False,
    allow_override=True,
    help="Print the GRR console version number and exit immediately.")

_Datapoint = Tuple[float, int]
_Datapoints = List[_Datapoint]
_TargetWithDatapoints = collections.namedtuple("TargetWithDatapoints",
                                               ["target", "datapoints"])
_TableQueryResult = collections.namedtuple("TableQueryResult",
                                           ["columns", "rows", "type"])


class JSONRequest(werkzeug_wrappers_json.JSONMixin, werkzeug_wrappers.Request):
  pass


class JSONResponse(werkzeug_wrappers_json.JSONMixin,
                   werkzeug_wrappers.Response):

  def __init__(self, response=None, *args, **kwargs) -> None:
    kwargs["mimetype"] = JSON_MIME_TYPE
    if response is not None and not isinstance(response,
                                               werkzeug_wsgi.ClosingIterator):
      response = json.dumps(response)
    super().__init__(response, *args, **kwargs)


class Metric(ABC):
  """A single metric that can be fetched from a
  Fleetspeak-based GRR deployment."""

  @abstractmethod
  def __init__(self, name: str) -> None:
    """Initializes a new metric."""
    self.name = name

  @abstractmethod
  def ProcessQuery(self, req: JSONRequest):
    """Processes the request JSON data and returns
    data that can be read by Grafana (by JSON Datasource plugin)."""
    pass


class ClientResourceUsageMetric(Metric):

  def __init__(self, name: str, record_values_extract_fn: Callable) -> None:
    super().__init__(name)
    self.record_values_extract_fn = record_values_extract_fn

  def ProcessQuery(self, req: JSONRequest) -> _TargetWithDatapoints:
    client_id = req["scopedVars"]["ClientID"]["value"]
    start_range_ts = timeToProtoTimestamp(req["range"]["from"])
    end_range_ts = timeToProtoTimestamp(req["range"]["to"])
    records_list = fleetspeak_utils.FetchClientResourceUsageRecords(
        client_id, start_range_ts, end_range_ts)
    record_values = self.record_values_extract_fn(records_list)
    datapoints = [(v, r.server_timestamp.seconds * 1000 +
                   r.server_timestamp.nanos // 1000000)
                  for (v, r) in zip(record_values, records_list)]
    return _TargetWithDatapoints(target=self.name, datapoints=datapoints)


class ClientsStatisticsMetric(Metric):

  def __init__(self, name: str, get_fleet_stats_fn: Callable,
               days_active: int) -> None:
    super().__init__(name)
    self.get_fleet_stats_fn = get_fleet_stats_fn
    self.days_active = days_active

  def ProcessQuery(self, req: JSONRequest) -> _TableQueryResult:
    fleet_stats = self.get_fleet_stats_fn(_FLEET_BREAKDOWN_DAY_BUCKETS)
    totals = fleet_stats.GetTotalsForDay(self.days_active)
    return _TableQueryResult(
      columns=[{
        "text": "Label", "type":"string"
      }, {
        "text": "Value", "type": "number"
      }],
      rows=[[l, v] for l, v in totals.items()],
      type="table")


AVAILABLE_METRICS_LIST: List[Metric]
AVAILABLE_METRICS_LIST = [
    ClientResourceUsageMetric(
        "Mean User CPU Rate", lambda records_list:
        [record.mean_user_cpu_rate for record in records_list]),
    ClientResourceUsageMetric(
        "Max User CPU Rate", lambda records_list:
        [record.max_user_cpu_rate for record in records_list]),
    ClientResourceUsageMetric(
        "Mean System CPU Rate", lambda records_list:
        [record.mean_system_cpu_rate for record in records_list]),
    ClientResourceUsageMetric(
        "Max System CPU Rate", lambda records_list:
        [record.max_system_cpu_rate for record in records_list]),
    # We multiply to convert from MiB to MB
    ClientResourceUsageMetric(
        "Mean Resident Memory MB", lambda records_list:
        [record.mean_resident_memory_mib * 1.049 for record in records_list]),
    ClientResourceUsageMetric(
        "Max Resident Memory MB", lambda records_list:
        [record.max_resident_memory_mib * 1.049 for record in records_list]),
]
AVAILABLE_METRICS_LIST.extend([
    ClientsStatisticsMetric(
        f"OS Platform Breakdown - {n_days} Day Active",
        lambda buckets: data_store.REL_DB.CountClientPlatformsByLabel(buckets),
        n_days) for n_days in _FLEET_BREAKDOWN_DAY_BUCKETS
])
AVAILABLE_METRICS_LIST.extend([
    ClientsStatisticsMetric(
        f"OS Release Version Breakdown - {n_days} Day Active", lambda buckets:
        data_store.REL_DB.CountClientPlatformReleasesByLabel(buckets), n_days)
    for n_days in _FLEET_BREAKDOWN_DAY_BUCKETS
])
AVAILABLE_METRICS_DICT = {
    metric.name: metric for metric in AVAILABLE_METRICS_LIST
}


class Grrafana(object):
  """GRRafana HTTP server instance.

  A full description of all endpoints implemented within this HTTP
  server can be found in:
  https://github.com/simPod/grafana-json-datasource#api."""

  def __init__(self) -> None:
    """Initializes a new GRRafana HTTP server instance."""
    self._url_map = werkzeug_routing.Map([
        werkzeug_routing.Rule("/",
                              endpoint=self._OnRoot,
                              methods=["GET"]),
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
    endpoint, values = adapter.match()
    return endpoint(request, **values)

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
      response = list(AVAILABLE_METRICS_DICT.keys())
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
    requested_targets = [entry["target"] for entry in json_data["targets"]]
    targets_with_datapoints = [
        AVAILABLE_METRICS_DICT[target].ProcessQuery(json_data)
        for target in requested_targets
    ]
    response = [t._asdict() for t in targets_with_datapoints]
    return JSONResponse(response=response)

  def _OnAnnotations(self, request: JSONRequest) -> JSONResponse:
    pass


def timeToProtoTimestamp(
    grafana_time: str) -> timestamp_pb2.Timestamp:
  date = dateutil.parser.parse(grafana_time)  # type: ignore
  return timestamp_pb2.Timestamp(seconds=int(date.timestamp()),
                                 nanos=date.microsecond * 1000)


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
