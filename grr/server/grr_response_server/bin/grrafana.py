#!/usr/bin/env python
"""GRRafana HTTP server implementation."""

import abc
import json
import types
from typing import Any, Callable, Dict, FrozenSet, Iterable, List, NamedTuple, Type

from absl import app
from absl import flags
from dateutil import parser
from werkzeug import routing as werkzeug_routing
from werkzeug import serving as werkzeug_serving
from werkzeug import wrappers as werkzeug_wrappers

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

_VERSION = flags.DEFINE_bool(
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
  def ProcessQuery(self, req: werkzeug_wrappers.Request) -> NamedTuple:
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
      req: werkzeug_wrappers.Request,
  ) -> _TargetWithDatapoints:  # type: ignore[override]
    req_json = req.get_json()

    client_id = req_json["scopedVars"]["ClientID"]["value"]
    start_range_ts = TimeToProtoTimestamp(req_json["range"]["from"])
    end_range_ts = TimeToProtoTimestamp(req_json["range"]["to"])

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
      self,
      req: werkzeug_wrappers.Request,
  ) -> _TableQueryResult:  # type: ignore[override]
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
        werkzeug_routing.Rule("/", endpoint=self._OnRoot, methods=["GET"]),  # pytype: disable=wrong-arg-types
        werkzeug_routing.Rule(
            "/search", endpoint=self._OnSearch, methods=["POST"]),  # pytype: disable=wrong-arg-types
        werkzeug_routing.Rule(
            "/query", endpoint=self._OnQuery, methods=["POST"]),  # pytype: disable=wrong-arg-types
        werkzeug_routing.Rule(
            "/annotations", endpoint=self._OnAnnotations, methods=["POST"]),  # pytype: disable=wrong-arg-types
    ])

  def _DispatchRequest(
      self,
      request: werkzeug_wrappers.Request,
  ) -> werkzeug_wrappers.Response:
    """Maps requests to different methods."""
    adapter = self._url_map.bind_to_environ(request.environ)
    endpoint, values = adapter.match()
    return endpoint(request, **values)  # pytype: disable=not-callable

  # pyformat: disable
  # pylint: disable=line-too-long
  # Good luck finding out what the types of these parameters are. Werkzeug's
  # documentation names `start_response` type as `StartResponse` [1] (super
  # helpful!) and refuses to elaborate what it is further. There is a Python PEP
  # that talks about some `start_response` [2] callable which may or may not be
  # the same thing and says that it is callable but it takes *at least* 10 para-
  # graphs to explain the type of arguments of this callable (and remaining 30
  # on its behaviour). The below description is my best guess what the type rea-
  # lly is but I refuse to take any responsibility for any issues this causes.
  # Please, direct your complaints to whoever approved a dynamic language to be
  # "production-ready".
  #
  # [1]: https://werkzeug.palletsprojects.com/en/2.2.x/wrappers/#werkzeug.wrappers.Response.__call__
  # [2]: https://peps.python.org/pep-0333/#the-start-response-callable
  # pyformat: enable
  # pylint: enable=line-too-long
  def __call__(
      self,
      environ: dict[str, Any],
      start_response: Callable[[str, list[tuple[str, Any]], tuple[Type[Exception], Exception, types.TracebackType]], Any]
  ) -> Iterable[bytes]:
    request = werkzeug_wrappers.Request(environ)
    response = self._DispatchRequest(request)
    return response(environ, start_response)

  def _OnRoot(
      self,
      unused_request: werkzeug_wrappers.Request,
  ) -> werkzeug_wrappers.Response:
    """Serves OK message to database connection check."""
    return werkzeug_wrappers.Response(content_type=JSON_MIME_TYPE)

  def _OnSearch(
      self,
      unused_request: werkzeug_wrappers.Request,
  ) -> werkzeug_wrappers.Response:
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
    return werkzeug_wrappers.Response(
        response=json.dumps(response), content_type=JSON_MIME_TYPE)

  def _OnQuery(
      self,
      request: werkzeug_wrappers.Request,
  ) -> werkzeug_wrappers.Response:
    """Retrieves datapoints for Grafana.

    Given a client ID as a Grafana variable and targets (resource usages),
    returns datapoints in a format Grafana can interpret.

    Args:
      request: JSON request.

    Returns:
      JSON response.
    """
    json_data = request.get_json()
    requested_targets = [entry["target"] for entry in json_data["targets"]]
    targets_with_datapoints = [
        AVAILABLE_METRICS_BY_NAME[target].ProcessQuery(request)
        for target in requested_targets
    ]
    response = [t._asdict() for t in targets_with_datapoints]
    return werkzeug_wrappers.Response(
        response=json.dumps(response), content_type=JSON_MIME_TYPE)

  def _OnAnnotations(
      self,
      unused_request: werkzeug_wrappers.Request,
  ) -> werkzeug_wrappers.Response:
    return werkzeug_wrappers.Response(content_type=JSON_MIME_TYPE)


def TimeToProtoTimestamp(grafana_time: str) -> timestamp_pb2.Timestamp:
  date = parser.parse(grafana_time)
  return timestamp_pb2.Timestamp(
      seconds=int(date.timestamp()), nanos=date.microsecond * 1000)


def main(argv: Any) -> None:
  """Main."""
  del argv  # Unused.

  if _VERSION.value:
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
