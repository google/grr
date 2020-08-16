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

  def __init__(self, config):
    self.url_map = Map([
    Rule('/', endpoint='root', methods=["GET"]),
    Rule('/search', endpoint='search', methods=["POST"]),
    Rule('/query', endpoint='query', methods=["POST"]),
    Rule('/annotations', endpoint='annotations', methods=["POST"])
    ])

  def dispatch_request(self, request):
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
    return JSONResponse()

  def on_search(self, request):
    if "type" in request.json:
      # Request issued on Panel > Queries page.
      response = fetch_available_metrics()
    else:
      # Grafana issued request on Variables > New/Edit page.
      response = fetch_client_ids()
    return JSONResponse(response=response, mimetype="application/json")

  def on_query(self, request):
    request_json_format = request.json
    requested_client_id = next(iter(request_json_format["scopedVars"].values()))["value"]
    requested_targets = [entry["target"] for entry in request_json_format["targets"]]
    response = fetch_datapoints(requested_client_id, request_json_format["maxDataPoints"], requested_targets)
    return JSONResponse(response=response, mimetype="application/json")

  def on_annotations(self, request):
    pass

def fetch_available_metrics():
  raw_data = fleetspeak_utils.GetAvailableMetricsFromFleetspeak()
  targets_list = list(raw_data.targets)
  targets_list.remove('client_id')
  return json.dumps(targets_list)

def fetch_client_ids():
  raw_data = fleetspeak_utils.GetClientIdsFromFleetspeak()
  clients_list = list(raw_data.clients)
  client_ids_list = list(map(
    lambda c: fleetspeak_utils.FleetspeakIDToGRRID(c.client_id), clients_list))
  return json.dumps(client_ids_list)

def fetch_datapoints(client_id, limit, targets):
  raw_data = fleetspeak_utils.FetchClientResourceUsageRecordsFromFleetspeak(client_id, limit)
  records_list = list(raw_data.records)
  response = list()
  for target in targets:
    datapoints_for_single_target = list(map(lambda r: [getattr(r, target), r.server_timestamp.seconds * 1000], records_list))
    response.append({"target": target, "datapoints": datapoints_for_single_target})
  return json.dumps(response)

def main(argv):
  del argv
  if flags.FLAGS.version:
    print("GRRafana server {}".format(config_server.VERSION["packageversion"]))
    return
  config.CONFIG.AddContext(contexts.GRRAFANA_CONTEXT, "Context applied when running GRRafana server.")
  server_startup.Init()
  fleetspeak_connector.Init()
  run_simple('127.0.0.1', 5000, Grrafana({}), use_debugger=True, use_reloader=True)


if __name__ == '__main__':
  app.run(main)