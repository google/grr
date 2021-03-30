#!/usr/bin/env python
"""GRRafana HTTP server implementation."""

import abc
import json
from typing import Any, Callable, Dict, FrozenSet, List, NamedTuple

from absl import app
from absl import flags
from dateutil import parser
from werkzeug import routing as werkzeug_routing
from werkzeug import serving as werkzeug_serving
from werkzeug import wrappers as werkzeug_wrappers
from werkzeug.wrappers import json as werkzeug_wrappers_json  # type: ignore

from google.protobuf import timestamp_pb2

from grr_response_core import config
from grr_response_core.config import contexts
from grr_response_core.config import server as config_server
from grr_response_server import data_store
from grr_response_server import fleet_utils
from grr_response_server import fleetspeak_connector
from grr_response_server import fleetspeak_utils
from grr_response_server import server_startup

from fleetspeak.src.server.proto.fleetspeak_server import resource_pb2

JSON_MIME_TYPE = "application/json"
_FLEET_BREAKDOWN_DAY_BUCKETS = frozenset([1, 7, 14, 30])

flags.DEFINE_bool(
    "version",
    default=False,
    allow_override=True,
    help="Print the GRR console version number and exit immediately.")


class _Datapoint(NamedTuple):
  """A datapoint represents a single time-value data point."""

  nanos: float
  value: int


_Datapoints = List[_Datapoint]


class _TargetWithDatapoints(NamedTuple):
  """A tuple that represents a processed resource usage data query."""

  target: str
  datapoints: _Datapoints


class _TableQueryResult(NamedTuple):
  """A tuple that represents a processed client statistics query."""

  columns: List[Dict[str, str]]
  rows: List[List[Any]]
  type: str


class JSONRequest(werkzeug_wrappers_json.JSONMixin, werkzeug_wrappers.Request):
  pass


class JSONResponse(werkzeug_wrappers_json.JSONMixin,
                   werkzeug_wrappers.Response):
  pass


class Metric(abc.ABC):
  """A single metric from a Fleetspeak-based GRR deployment."""

  def __init__(self, name: str) -> None:
    """Initializes a new metric."""
    self._name = name

  @property
  def name(self) -> str:
    """Returns the name of the metric."""
    return self._name

  @abc.abstractmethod
  def ProcessQuery(self, req: JSONRequest) -> NamedTuple:
    """Processes the request JSON data into Grafana-recognisable format."""
    pass


class ClientResourceUsageMetric(Metric):
  """A metric that represents resource usage data for a single client."""

  def __init__(
      self, name: str, record_values_extract_fn: Callable[
          [List[resource_pb2.ClientResourceUsageRecord]], List[float]]
  ) -> None:
    super().__init__(name)
    self._record_values_extract_fn = record_values_extract_fn

  # Note: return type error issues at python/mypy#3915, python/typing#431
  def ProcessQuery(
      self,
      req: JSONRequest) -> _TargetWithDatapoints:  # type: ignore[override]
    client_id = req["scopedVars"]["ClientID"]["value"]
    start_range_ts = TimeToProtoTimestamp(req["range"]["from"])
    end_range_ts = TimeToProtoTimestamp(req["range"]["to"])
    records_list = fleetspeak_utils.FetchClientResourceUsageRecords(
        client_id, start_range_ts, end_range_ts)
    record_values = self._record_values_extract_fn(records_list)

    datapoints = []
    for (v, r) in zip(record_values, records_list):
      datapoints.append(
          _Datapoint(
              nanos=v,
              value=r.server_timestamp.seconds * 1000 +
              r.server_timestamp.nanos // 1000000))

    return _TargetWithDatapoints(target=self._name, datapoints=datapoints)


class ClientsStatisticsMetric(Metric):
  """A metric that represents aggregated client stats."""

  def __init__(self, name: str,
               get_fleet_stats_fn: Callable[[FrozenSet[int]],
                                            fleet_utils.FleetStats],
               days_active: int) -> None:
    super().__init__(name)
    self._get_fleet_stats_fn = get_fleet_stats_fn
    self._days_active = days_active

  # Note: return type error issues at python/mypy#3915, python/typing#431
  def ProcessQuery(
      self, req: JSONRequest) -> _TableQueryResult:  # type: ignore[override]
    fleet_stats = self._get_fleet_stats_fn(_FLEET_BREAKDOWN_DAY_BUCKETS)
    totals = fleet_stats.GetTotalsForDay(self._days_active)
    return _TableQueryResult(
        columns=[{
            "text": "Label",
            "type": "string"
        }, {
            "text": "Value",
            "type": "number"
        }],
        rows=[[l, v] for l, v in totals.items()],
        type="table")


AVAILABLE_METRICS_LIST: List[Metric]
AVAILABLE_METRICS_LIST = [
    ClientResourceUsageMetric("Mean User CPU Rate",
                              lambda rl: [r.mean_user_cpu_rate for r in rl]),
    ClientResourceUsageMetric("Max User CPU Rate",
                              lambda rl: [r.max_user_cpu_rate for r in rl]),
    ClientResourceUsageMetric("Mean System CPU Rate",
                              lambda rl: [r.mean_system_cpu_rate for r in rl]),
    ClientResourceUsageMetric("Max System CPU Rate",
                              lambda rl: [r.max_system_cpu_rate for r in rl]),
    # Converting MiB to MB
    ClientResourceUsageMetric(
        "Mean Resident Memory MB",
        lambda rl: [r.mean_resident_memory_mib * 1.049 for r in rl]),
    ClientResourceUsageMetric(
        "Max Resident Memory MB",
        lambda rl: [r.max_resident_memory_mib * 1.049 for r in rl]),
]
# pylint: disable=unnecessary-lambda
# Lambdas below are needed, since data_store.REL_DB is initialized at runtime,
# so referencing it at the top level won't work.
client_statistics_names_fns = [
    (lambda n_days: f"OS Platform Breakdown - {n_days} Day Active",
     lambda bs: data_store.REL_DB.CountClientPlatformsByLabel(bs)),
    (lambda n_days: f"OS Release Version Breakdown - {n_days} Day Active",
     lambda bs: data_store.REL_DB.CountClientPlatformReleasesByLabel(bs)),
    (lambda n_days: f"Client Version Strings - {n_days} Day Active",
     lambda bs: data_store.REL_DB.CountClientVersionStringsByLabel(bs))
]
# pylint: enable=unnecessary-lambda
for metric_name_fn, metric_extract_fn in client_statistics_names_fns:
  for n_days in _FLEET_BREAKDOWN_DAY_BUCKETS:
    AVAILABLE_METRICS_LIST.append(
        ClientsStatisticsMetric(
            metric_name_fn(n_days), metric_extract_fn, n_days))
AVAILABLE_METRICS_BY_NAME = {
    metric.name: metric for metric in AVAILABLE_METRICS_LIST
}


class Grrafana(object):
  """GRRafana HTTP server instance.

  A full description of all endpoints implemented within this HTTP
  server can be found in:
  https://github.com/simPod/grafana-json-datasource#api.
  """

  def __init__(self) -> None:
    """Initializes a new GRRafana HTTP server instance."""
    self._url_map = werkzeug_routing.Map([
        werkzeug_routing.Rule("/", endpoint=self._OnRoot, methods=["GET"]),
        werkzeug_routing.Rule(
            "/search", endpoint=self._OnSearch, methods=["POST"]),
        werkzeug_routing.Rule(
            "/query", endpoint=self._OnQuery, methods=["POST"]),
        werkzeug_routing.Rule(
            "/annotations", endpoint=self._OnAnnotations, methods=["POST"]),
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

  def _OnRoot(self, unused_request: JSONRequest) -> JSONResponse:
    """Serves OK message to database connection check."""
    return JSONResponse(content_type=JSON_MIME_TYPE)

  def _OnSearch(self, unused_request: JSONRequest) -> JSONResponse:
    """Fetches available resource usage metrics.

    Depending on the type of request Grafana is issuing, this method returns
    either available client resource usage metrics from the constant
    AVAILABLE_METRICS, or possible values for a defined Grafana variable.

    Args:
      unused_request: JSON request.

    Returns:
      JSON response.
    """
    response = list(AVAILABLE_METRICS_BY_NAME.keys())
    return JSONResponse(
        response=json.dumps(response), content_type=JSON_MIME_TYPE)

  def _OnQuery(self, request: JSONRequest) -> JSONResponse:
    """Retrieves datapoints for Grafana.

    Given a client ID as a Grafana variable and targets (resource usages),
    returns datapoints in a format Grafana can interpret.

    Args:
      request: JSON request.

    Returns:
      JSON response.
    """
    json_data = request.json
    requested_targets = [entry["target"] for entry in json_data["targets"]]
    targets_with_datapoints = [
        AVAILABLE_METRICS_BY_NAME[target].ProcessQuery(json_data)
        for target in requested_targets
    ]
    response = [t._asdict() for t in targets_with_datapoints]
    return JSONResponse(
        response=json.dumps(response), content_type=JSON_MIME_TYPE)

  def _OnAnnotations(self, unused_request: JSONRequest) -> JSONResponse:
    return JSONResponse(content_type=JSON_MIME_TYPE)


def TimeToProtoTimestamp(grafana_time: str) -> timestamp_pb2.Timestamp:
  date = parser.parse(grafana_time)
  return timestamp_pb2.Timestamp(
      seconds=int(date.timestamp()), nanos=date.microsecond * 1000)


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
  werkzeug_serving.run_simple(config.CONFIG["GRRafana.bind"],
                              config.CONFIG["GRRafana.port"], Grrafana())


if __name__ == "__main__":
  app.run(main)
