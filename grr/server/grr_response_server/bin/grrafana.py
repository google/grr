import os
import json
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

  def __init__(self, config):
    """Constructor."""
    self.url_map = Map([
    Rule('/', endpoint='root', methods=["GET"]),
    Rule('/search', endpoint='search', methods=["POST"]),
    Rule('/query', endpoint='query', methods=["POST"]),
    Rule('/annotations', endpoint='annotations', methods=["POST"])
    ])

  def dispatch_request(self, request):
    """Maps requests to different methods."""
    adapter = self.url_map.bind_to_environ(request.environ)
    try:
      endpoint, values = adapter.match()
      return getattr(self, 'on_' + endpoint)(request, **values)
    except HTTPException as e:
      return e

  def wsgi_app(self, environ, start_response):
    request = JSONRequest(environ)
    response = self.dispatch_request(request)
    return response(environ, start_response)

  def __call__(self, environ, start_response):
    return self.wsgi_app(environ, start_response)

  def on_root(self, request):
    """Returns OK message to database connection check."""
    return JSONResponse()

  def on_search(self, request):
    """Depending on the request type, returns either available client
    resource usage metrics from Fleetspeak database, or possible values
    for a defined Grafana variable (currently supports only variables based
    on client IDs)."""
    if "type" in request.json:
      # Request issued on Panel > Queries page.
      response = fetch_available_metrics()
    else:
      # Grafana issued request on Variables > New/Edit page.
      response = fetch_client_ids()  # todo: support Grafana variables other than ClientID.
    return JSONResponse(response=json.dumps(response), mimetype="application/json")

  def on_query(self, request):
    """Given a client ID as a Grafana variable and targets (resource usages),
    returns datapoints in a format Grafana can interpret."""
    request_json_format = request.json
    requested_client_id = extract_client_id_from_variable(request_json_format)  # There must be a ClientID variable declated in Grafana.
    requested_targets = [entry["target"] for entry in request_json_format["targets"]]
    response = fetch_datapoints_for_targets(requested_client_id, request_json_format["maxDataPoints"], requested_targets)
    return JSONResponse(response=json.dumps(response), mimetype="application/json")

  def on_annotations(self, request):
    pass


def fetch_available_metrics():
  """Fetches available client resource usage records from Fleetspeak database.""" 
  return fleetspeak_utils.GetAvailableMetricsFromFleetspeak()


def fetch_client_ids():
  """Fetches GRR client IDs that have resource usage records in Fleetspeak database."""
  return fleetspeak_utils.GetClientIdsFromFleetspeak()


def fetch_datapoints_for_targets(client_id, limit, targets):
  """Fetches an array of <datapoint, timestamp> tuples for each target metric from Fleetspeak database."""
  records_list = fleetspeak_utils.FetchClientResourceUsageRecordsFromFleetspeak(client_id, limit)
  response = list()
  for target in targets:
    datapoints_for_single_target = [[getattr(record, target), record.server_timestamp.seconds * 1000] for record in records_list]
    response.append({"target": target, "datapoints": datapoints_for_single_target})
  return response


def extract_client_id_from_variable(req):
  """Extracts the client ID from a Grafana JSON request."""
  # Based on an assumption that there is only one Grafana variable.
  return next(iter(req["scopedVars"].values()))["value"]


def main(argv):
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
